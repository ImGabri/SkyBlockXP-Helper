"""Exercise real pet-care code at a fixture boundary, never a live game server."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("care_adapter_fixture", ROOT / "tests/test_adapter.py")
adapter_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter_tests)
builder = adapter_tests.builder
FIXTURE = adapter_tests.FIXTURE + r'''
library.ClassName = "ModuleScript"
local inventory = {}
for i = 1, 12 do inventory[i] = { uid = "normal-" .. i, id = "cat" } end
for i = 1, 6 do table.insert(inventory, { uid = "gold-" .. i, id = "cat", g = true }) end
local save = { Pets = inventory, Coins = 1000000 }
local directory = {
    Pets = { cat = { name = "Cat", rarity = "Basic" }, dog = { name = "Dog", rarity = "Basic" } },
    Eggs = { ["Starter Egg"] = { currency = "Coins", cost = 100, hatchable = true } },
}
local facade = {
    Network = network, PetCmds = exports[petsModule], Directory = directory,
    Save = { Get = function() return save end },
}
exports[library] = facade
local careResponse = true
local careHook
network.Invoke = function(command, ...)
    table.insert(calls, { method = "Invoke", command = command, args = table.pack(...) })
    if careHook then return careHook(command, ...) end
    return careResponse
end
local playerGui = instance("PlayerGui", "PlayerGui")
function player:FindFirstChild(name) if name == "PlayerGui" then return playerGui end end
for _, name in ipairs({ "Golden", "Rainbow", "Inventory", "Eggs" }) do
    local gui = instance(name, "ScreenGui", playerGui)
    gui.Enabled = false
end
'''


class CareTests(unittest.TestCase):
    def run_case(self, case):
        with tempfile.TemporaryDirectory(prefix="psx-care-") as temporary:
            root = Path(temporary)
            sources = root / "src"
            sources.mkdir()
            for name in ["Config.luau", "ConversionPolicy.luau"]:
                shutil.copyfile(ROOT / "src/client" / name, sources / name)
            source = ROOT / "src/client/PetCare.luau"
            (sources / "PetCare.luau").write_text(source.read_text() if source.exists() else 'return {new=function() return {} end}\n')
            (sources / "init.client.luau").write_text(
                'local PetCare = require(script.PetCare)\nlocal care = PetCare.new()\n'
                'assert(type(care.Connect) == "function", "pet-care integration missing")\n'
                + case + '\nprint("CARE_TEST_OK")\n')
            output = root / "care.lua"
            output.write_text(FIXTURE + builder.build_bundle(sources))
            result = subprocess.run([str(ROOT / ".tools/bin/luau"), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("CARE_TEST_OK", result.stdout)

    def test_constructor_is_passive_and_loading_does_not_probe_coins(self):
        self.run_case('''
assert(nativeCalls == 0 and #calls == 0)
care:Connect()
assert(care.Supported.AutoHatch and care.Supported.AutoGold and care.Supported.AutoRainbow, care.Reason)
assert(nativeCalls == 1 and #calls == 0, "pet tools invoked a remote while loading")
''')

    def test_hatch_modes_have_exact_legacy_arguments(self):
        for mode, triple, octuple in [("Single", "false", "false"), ("Triple", "true", "false"), ("Octuple", "false", "true")]:
            with self.subTest(mode=mode):
                self.run_case(f'''
care:Connect()
assert(care:Hatch("Starter Egg", "{mode}") == 1)
assert(#calls == 1 and calls[1].command == "Buy Egg")
local args = calls[1].args
assert(args.n == 3 and args[1] == "Starter Egg" and args[2] == {triple} and args[3] == {octuple})
''')

    def test_unknown_premium_unaffordable_eggs_and_invalid_modes_send_nothing(self):
        for change, egg, mode in [('', 'Unknown', 'Single'), ('directory.Eggs["Starter Egg"].currency = "Robux"', 'Starter Egg', 'Single'), ('save.Coins = 0', 'Starter Egg', 'Single'), ('', 'Starter Egg', 'Ten')]:
            with self.subTest(change=change, egg=egg, mode=mode):
                self.run_case(change + f'''
care:Connect()
assert(not pcall(care.Hatch, care, "{egg}", "{mode}"))
assert(#calls == 0)
''')

    def test_gold_and_rainbow_dispatch_six_of_correct_variant_only(self):
        for variant, command, prefix in [("Gold", "Use Golden Machine", "normal-"), ("Rainbow", "Use Rainbow Machine", "gold-")]:
            with self.subTest(variant=variant):
                self.run_case(f'''
care:Connect()
assert(care:Convert("{variant}", "Cat") == 1)
assert(#calls == 1 and calls[1].command == "{command}")
local args = calls[1].args
assert(args.n == 1 and #args[1] == 6)
local seen = {{}}
for _, uid in ipairs(args[1]) do
    assert(not seen[uid] and string.find(uid, "{prefix}", 1, true) == 1)
    seen[uid] = true
end
''')

    def test_no_selected_species_no_batch_and_protected_pets_are_not_consumed(self):
        for field in ["lk", "locked", "favorite", "fav", "hc", "sh", "dm"]:
            with self.subTest(field=field):
                self.run_case(f'''
for _, pet in ipairs(inventory) do if not pet.g then pet.{field} = true end end
care:Connect()
assert(care:Convert("Gold", "cat") == 0)
assert(not pcall(care.Convert, care, "Gold", ""))
assert(#calls == 0)
''')

    def test_equipped_duplicate_and_premium_pets_are_excluded(self):
        for change in [
            'equipped = inventory',
            'for _, pet in ipairs(inventory) do if not pet.g then pet.uid = "duplicate" end end',
            'directory.Pets.cat.rarity = "Exclusive"',
            'directory.Pets.cat.huge = true',
            'directory.Pets.cat.titanic = true',
            'directory.Pets.cat.isPremium = true',
        ]:
            with self.subTest(change=change):
                self.run_case(change + '''
care:Connect()
assert(care:Convert("Gold", "cat") == 0)
assert(#calls == 0)
''')

    def test_consumed_uids_stay_reserved_while_save_replication_lags(self):
        self.run_case('''
care:Connect()
assert(care:Convert("Gold", "cat") == 1)
assert(care:Convert("Gold", "cat") == 1)
assert(care:Convert("Gold", "cat") == 0)
local seen = {}
for _, call in ipairs(calls) do
    for _, uid in ipairs(call.args[1]) do assert(not seen[uid], "same UID submitted twice"); seen[uid] = true end
end
''')

    def test_empty_or_rejected_responses_stop_feature_without_claiming_success(self):
        for response in ["return", "return false", "return {}"]:
            with self.subTest(response=response):
                self.run_case('''
care:Connect()
careHook = function() ''' + response + ''' end
assert(not pcall(care.Hatch, care, "Starter Egg", "Single"))
assert(care.Supported.AutoHatch == false)
assert(#calls == 1)
assert(not pcall(care.Hatch, care, "Starter Egg", "Single"))
assert(#calls == 1, "rejected feature sent another request")
''')

    def test_canceled_calls_and_wrong_place_send_nothing(self):
        self.run_case('''
care:Connect()
assert(care:Hatch("Starter Egg", "Single", function() return false end) == 0)
assert(care:Convert("Gold", "cat", function() return false end) == 0)
assert(#calls == 0)
game.PlaceId = 1
care:Connect()
assert(not care.Supported.AutoHatch)
assert(not pcall(care.Hatch, care, "Starter Egg", "Single"))
assert(#calls == 0)
''')

    def test_timeout_during_save_read_prevents_spending(self):
        self.run_case('''
local live = true
facade.Save.Get = function() live = false; return save end
care:Connect()
assert(care:Hatch("Starter Egg", "Single", function() return live end) == 0)
assert(#calls == 0)
''')

    def test_native_menus_restore_original_state_without_networking(self):
        self.run_case('''
care:Connect()
assert(care:OpenMenu("Gold"))
assert(playerGui:FindFirstChild("Golden").Enabled)
assert(care:OpenMenu("Rainbow"))
assert(care:OpenMenu("Egg"))
assert(care:OpenMenu("Inventory"))
assert(#calls == 0)
care:Destroy()
for _, gui in ipairs(playerGui:GetChildren()) do assert(not gui.Enabled) end
assert(not pcall(care.OpenMenu, care, "Gold"))
''')

    def test_missing_or_ambiguous_species_and_unknown_inventory_are_rejected(self):
        for change in ['directory.Pets.dog.name = "Cat"', 'save.Pets = nil', 'inventory[1].uid = {}']:
            with self.subTest(change=change):
                self.run_case(change + '''
care:Connect()
assert(not pcall(care.Convert, care, "Gold", "Cat"))
assert(#calls == 0)
''')
