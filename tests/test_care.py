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
local boundaryTypeof = typeof
local function typeof(value)
    if type(value) == "table" and value.ClassName then return "Instance" end
    return boundaryTypeof(value)
end
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
local eggModel = instance("Starter Egg Model", "Model", workspace)
eggModel.Attributes.ID = "Starter Egg"
part("Center", Vector3.new(20, 0, 0), eggModel)
function eggModel:IsDescendantOf(parent)
    local node = self.Parent
    while node do if node == parent then return true end; node = node.Parent end
    return false
end
facade.WorldCmds = { GetAllEggs = function() return { eggModel } end }
local saveModule = instance("Save", "ModuleScript", client)
local directoryModule = instance("Directory", "ModuleScript", library)
local worldModule = instance("WorldCmds", "ModuleScript", client)
exports[saveModule], exports[directoryModule], exports[worldModule] = facade.Save, directory, facade.WorldCmds
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
local frame = instance("Frame", "Frame", playerGui:FindFirstChild("Inventory"))
local main = instance("Main", "Frame", frame)
local slots = instance("Pets", "Frame", main)
local normalSlots = instance("Normal", "Frame", slots)
for _, pet in ipairs(inventory) do
    local slot = instance(pet.uid, "TextButton", normalSlots)
    local locked = instance("Locked", "ImageLabel", slot)
    locked.Visible = false
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

    def test_direct_mode_loads_known_child_modules_and_no_facade(self):
        self.run_case('''
client.ClassName = "ModuleScript"
local saveModule = instance("Save", "ModuleScript", client)
local directoryModule = instance("Directory", "ModuleScript", library)
exports[saveModule] = facade.Save
exports[directoryModule] = directory
assert(nativeCalls == 0)
care:Connect(nil, "Direct")
assert(care.Supported.AutoHatch and care.Supported.AutoGold and care.Supported.AutoRainbow, care.Reason)
assert(nativeCalls == 4 and #calls == 0, "Direct mode must load exactly four modules with no requests")
contains(care.Report, "Module path mode: Direct")
''')

    def test_direct_mode_reports_stalled_first_child_module(self):
        self.run_case('''
client.ClassName = "ModuleScript"
local original = require
require = function(module)
    if module == networkModule then coroutine.yield("child module loading") end
    return original(module)
end
local worker = coroutine.create(function() care:Connect(nil, "Direct") end)
assert(coroutine.resume(worker))
contains(care.Report, "Loading Library.Client.Network directly")
assert(nativeCalls == 0 and #calls == 0)
assert(coroutine.close(worker))
''')

    def test_rejected_or_canceled_connect_keeps_the_existing_module_mode(self):
        self.run_case('''
facade.Save.Get=function() coroutine.yield("pending save");return save end
care:Connect(nil,"Facade")
local worker=coroutine.create(function() care:Hatch("Starter Egg","Single") end)
assert(coroutine.resume(worker))
assert(not pcall(care.Connect,care,nil,"Direct"))
assert(care._mode=="Facade","busy rejected connect changed the live module mode")
assert(coroutine.close(worker))
care:Connect(function() return false end,"Direct")
assert(care._mode=="Facade","canceled connect changed the live module mode")
''')

    def test_direct_egg_lookup_is_lazy_and_uses_its_current_operation_token(self):
        self.run_case('''
client.ClassName="ModuleScript"
local saveModule=instance("Save","ModuleScript",client)
local directoryModule=instance("Directory","ModuleScript",library)
local worldModule=instance("WorldCmds","ModuleScript",client)
exports[saveModule]=facade.Save
exports[directoryModule]=directory
exports[worldModule]=facade.WorldCmds
exports[library]={}
local preparing=true
care:Connect(function() return preparing end,"Direct")
assert(nativeCalls==4 and #calls==0,"Direct preparation eagerly loaded world or facade")
preparing=false
assert(care:GetEggTarget("Starter Egg")==eggModel,"egg lookup reused an expired preparation token")
assert(nativeCalls==5 and #calls==0)
assert(care:GetEggTarget("Starter Egg",function() return false end)==nil)
assert(nativeCalls==5,"canceled egg lookup required another game module")
''')

    def test_save_inspector_keeps_ownership_during_proxy_shape_reads(self):
        self.run_case('''
local attempted,allowed=false,false
local oldSave=setmetatable({}, {__index=function(_,key)
    if key=="Pets" and not attempted then
        attempted=true
        facade.Save.Get=function() return save end
        allowed=pcall(care.Connect,care)
    end
    return nil
end})
facade.Save.Get=function() return oldSave end
care:Connect()
assert(care:InspectSave())
assert(attempted and not allowed,"shape inspection released ownership before native getters finished")
care:Connect()
assert(care.Supported.AutoGold and care.Supported.AutoRainbow,"fresh valid connection stayed disabled")
assert(#calls==0)
''')

    def test_canceled_save_shape_read_cannot_disable_capabilities_or_continue_reads(self):
        self.run_case('''
local live=true
local afterCancel=0
local value=setmetatable({}, {__index=function(_,key)
    if not live then afterCancel+=1 end
    if key=="Pets" then live=false end
    return nil
end})
facade.Save.Get=function() return value end
care:Connect()
assert(care:InspectSave(function() return live end)==false)
assert(care.Supported.AutoGold and care.Supported.AutoRainbow,"canceled inspection disabled the connection")
assert(afterCancel==0,"canceled shape inspection continued reading proxy fields")
assert(#calls==0)
''')

    def test_nil_hatch_save_disables_mutations_and_reports_the_actual_shape(self):
        self.run_case('''
facade.Save.Get=function() return nil end
care:Connect()
assert(not pcall(care.CanHatch,care,"Starter Egg","Single"))
assert(not care.Supported.AutoHatch and not care.Supported.AutoGold and not care.Supported.AutoRainbow)
contains(care.Reason,"Save.Get")
contains(care.Report,"Save.Get result type=nil")
assert(#calls==0)
''')

    def test_read_only_save_inspector_reports_shapes_without_mutation(self):
        self.run_case('''
care:Connect()
assert(care:InspectSave())
contains(care.Report, "Save.Get result type=table")
contains(care.Report, "Pets=table")
assert(not string.find(care.Report, "normal-1", 1, true), "pet UID leaked into diagnostics")
assert(#calls == 0, "inspection sent a game mutation request")
''')

    def test_read_only_save_inspector_reports_missing_pets_without_guessing(self):
        self.run_case('''
facade.Save.Get = function() return { Data = { Pets = inventory } } end
care:Connect()
assert(care:InspectSave())
contains(care.Report, "Pets=nil")
contains(care.Report, "Data.Pets=table")
assert(not pcall(care.Convert, care, "Gold", "cat"), "conversion guessed nested save layout")
assert(#calls == 0, "invalid save shape triggered a mutation")
assert(#care._reserved == 0 or next(care._reserved) == nil)
''')

    def test_nil_save_inspection_disables_mutations_without_sending_requests(self):
        self.run_case('''
facade.Save.Get = function() return nil end
care:Connect()
assert(care:InspectSave())
assert(not care.Supported.AutoGold and not care.Supported.AutoRainbow and not care.Supported.AutoHatch)
contains(care.Report, "Save.Get call: returns=1; first type=nil")
assert(#calls == 0, "nil save must not send any mutating request")
''')

    def test_read_only_save_inspector_distinguishes_zero_return_values(self):
        self.run_case('''
facade.Save.Get = function() return end
care:Connect()
assert(care:InspectSave())
contains(care.Report, "Save.Get call: returns=0; first type=none")
assert(not care.Supported.AutoGold)
assert(#calls == 0)
''')

    def test_read_only_save_inspector_handles_nil_data_without_remote_calls(self):
        self.run_case('''
facade.Save.Get = function() return nil end
care:Connect()
assert(care:InspectSave())
contains(care.Report, "Save.Get result type=nil")
assert(not pcall(care.CanConvert, care, "Gold", "cat"))
assert(#calls == 0)
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

    def test_catalog_selection_cycles_real_directory_choices_without_remote_calls(self):
        self.run_case('''
care:Connect()
assert(type(care.NextChoice) == "function", "directory selection missing")
local egg = care:NextChoice("Egg", "")
assert(egg == "Starter Egg")
assert(care:NextChoice("Egg", egg) == egg)
local species = care:NextChoice("Species", "")
assert(species == "cat")
assert(care:NextChoice("Species", species) == "dog")
assert(#calls == 0)
''')

    def test_numeric_species_directory_keys_can_be_selected_by_id(self):
        self.run_case('''
directory.Pets[12] = directory.Pets.cat
directory.Pets.cat = nil
for _, pet in ipairs(inventory) do pet.id = 12 end
care:Connect()
assert(care:Convert("Gold", "12") == 1)
assert(#calls == 1)
''')

    def test_unknown_premium_unaffordable_eggs_and_invalid_modes_send_nothing(self):
        for change, egg, mode in [('', 'Unknown', 'Single'), ('directory.Eggs["Starter Egg"].currency = "Robux"', 'Starter Egg', 'Single'), ('', 'Starter Egg', 'Ten')]:
            with self.subTest(change=change, egg=egg, mode=mode):
                self.run_case(change + f'''
care:Connect()
assert(not pcall(care.Hatch, care, "{egg}", "{mode}"))
assert(#calls == 0)
''')

    def test_hatch_readiness_waits_for_currency_without_disabling_or_spending(self):
        self.run_case('''
care:Connect()
assert(type(care.CanHatch) == "function", "hatch readiness missing")
save.Coins = 0
assert(not care:CanHatch("Starter Egg", "Single"))
assert(care:Hatch("Starter Egg", "Single") == 0)
assert(care.Supported.AutoHatch and #calls == 0)
contains(care.Reason, "Waiting")
save.Coins = 1000
assert(care:CanHatch("Starter Egg", "Triple"))
assert(care:Hatch("Starter Egg", "Triple") == 1)
assert(#calls == 1)
''')

    def test_selected_egg_target_is_a_unique_loaded_model_with_matching_id(self):
        self.run_case('''
care:Connect()
assert(type(care.GetEggTarget) == "function", "egg target resolver missing")
assert(care:GetEggTarget("Starter Egg") == eggModel)
assert(#calls == 0)
eggModel.Attributes.ID = "Other Egg"
assert(not pcall(care.GetEggTarget, care, "Starter Egg"))
eggModel.Attributes.ID = "Starter Egg"
eggModel.Parent = nil
assert(not pcall(care.GetEggTarget, care, "Starter Egg"))
assert(#calls == 0)
''')

    def test_missing_or_canceled_public_egg_list_never_returns_a_target(self):
        self.run_case('''
facade.WorldCmds = nil
care:Connect()
assert(type(care.GetEggTarget) == "function", "egg target resolver missing")
assert(not pcall(care.GetEggTarget, care, "Starter Egg"))
local live = true
facade.WorldCmds = { GetAllEggs = function() live = false; return { eggModel } end }
care:Connect()
assert(care:GetEggTarget("Starter Egg", function() return live end) == nil)
assert(#calls == 0)
''')

    def test_duplicate_loaded_egg_ids_are_rejected_without_guessing(self):
        self.run_case('''
facade.WorldCmds.GetAllEggs = function() return { eggModel, eggModel } end
care:Connect()
assert(type(care.GetEggTarget) == "function", "egg target resolver missing")
assert(not pcall(care.GetEggTarget, care, "Starter Egg"))
assert(#calls == 0)
''')

    def test_suspended_inventory_calls_identify_the_actual_read_stage(self):
        for source, expected in [('facade.Save.Get', 'Save.Get'), ('exports[petsModule].GetEquipped', 'GetEquipped')]:
            with self.subTest(source=source):
                self.run_case(source + ''' = function() coroutine.yield("native read"); return {} end
care:Connect()
local worker = coroutine.create(function() care:CanConvert("Gold", "cat") end)
assert(coroutine.resume(worker))
contains(care.Report, "''' + expected + '''")
assert(#calls == 0)
assert(coroutine.close(worker))
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

    def test_conversion_readiness_checks_batch_without_sending_or_reserving_pets(self):
        self.run_case('''
care:Connect()
assert(type(care.CanConvert) == "function", "conversion readiness missing")
assert(care:CanConvert("Gold", "cat"))
assert(#calls == 0, "readiness sent a conversion request")
assert(care:Convert("Gold", "cat") == 1)
assert(care:Convert("Gold", "cat") == 1)
assert(not care:CanConvert("Gold", "cat"))
assert(not care:CanConvert("Gold", "cat", function() return false end))
assert(#calls == 2)
''')

    def test_no_selected_species_no_batch_and_protected_pets_are_not_consumed(self):
        for field in ["l", "lk", "locked", "favorite", "fav", "hc", "sh", "dm"]:
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
            'directory.Pets.cat.isGift = true',
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

    def test_missing_or_locked_inventory_slots_cannot_be_converted(self):
        for change in ['normalSlots.Children = {}', 'for _, slot in ipairs(normalSlots:GetChildren()) do slot:FindFirstChild("Locked").Visible = true end']:
            with self.subTest(change=change):
                self.run_case(change + '''
care:Connect()
assert(care:Convert("Gold", "cat") == 0)
assert(#calls == 0, "missing/locked UI slots allowed consuming pets")
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

    def test_distance_rejection_preserves_server_message_and_allows_manual_retry(self):
        self.run_case('''
care:Connect()
careHook = function() return false, "You are too far away from the machine!" end
local ok, message = pcall(care.Convert, care, "Gold", "cat")
assert(not ok)
contains(tostring(message), "too far away from the machine")
assert(care.Supported.AutoGold, "recoverable range rejection permanently disabled gold")
local rejected = calls[1].args[1]
careHook = nil
assert(care:Convert("Gold", "cat") == 1)
local retried = calls[2].args[1]
for i = 1, 6 do assert(rejected[i] == retried[i], "distance rejection stranded unconsumed pet UIDs") end
''')

    def test_unknown_rejection_message_is_visible_but_does_not_release_uncertain_pets(self):
        self.run_case('''
care:Connect()
careHook = function() return false, "Machine request denied" end
local ok, message = pcall(care.Convert, care, "Rainbow", "cat")
assert(not ok)
contains(tostring(message), "Machine request denied")
careHook = nil
care:Connect()
assert(care:Convert("Rainbow", "cat") == 0, "uncertain rejected pets were automatically reused")
assert(#calls == 1)
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

    def test_loading_report_identifies_loader_before_native_require_returns(self):
        self.run_case('''
local native = require
require = function(module) coroutine.yield("module initializing"); return native(module) end
local worker = coroutine.create(function() care:Connect() end)
assert(coroutine.resume(worker))
contains(care.Report, "Pet-tool loader: require")
contains(care.Report, "Loading pet API facade")
assert(#calls == 0)
assert(coroutine.close(worker))
''')

    def test_loading_report_names_a_suspended_lazy_save_export(self):
        self.run_case('''
local saveApi = facade.Save
facade.Save = nil
setmetatable(facade, { __index = function(_, key)
    if key == "Save" then coroutine.yield("Save initializing"); return saveApi end
end })
local worker = coroutine.create(function() care:Connect() end)
assert(coroutine.resume(worker))
contains(care.Report, "Library.Save")
assert(#calls == 0)
assert(coroutine.close(worker))
''')

    def test_native_cancellation_releases_busy_owner_after_thread_is_closed(self):
        self.run_case('''
facade.Save.Get = function() coroutine.yield("native read"); return save end
care:Connect()
local worker = coroutine.create(function() care:Hatch("Starter Egg", "Single") end)
assert(coroutine.resume(worker))
assert(not pcall(care.Connect, care), "uncanceled native worker did not keep its slot")
assert(coroutine.close(worker))
assert(pcall(care.Connect, care), "closed native worker left pet tools permanently busy")
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
