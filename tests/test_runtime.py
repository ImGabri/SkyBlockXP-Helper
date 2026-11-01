"""Exercise the real Runtime and Jobs against explicit native-service boundaries.

These fixtures prove local lifecycle/cancellation behavior. They do not establish
executor compatibility, a working game protocol, or game-side rewards.
"""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_test_builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


FIXTURE = r'''
local clock = 100
local os = { clock = function() return clock end }
local taskErrors, spawned = {}, {}
local nativeCancelThrows = false
local setclipboard
local task = {}
function task.spawn(callback)
    local thread = coroutine.create(callback)
    table.insert(spawned, thread)
    local ok, message = coroutine.resume(thread)
    if not ok then table.insert(taskErrors, tostring(message)) end
    return thread
end
function task.wait() return coroutine.yield("task.wait") end
function task.cancel(thread)
    if nativeCancelThrows then error("Native cancellation unavailable") end
    coroutine.close(thread)
end

local function signal()
    local listeners = {}
    return {
        Connect = function(_, callback)
            local connection = { Connected = true }
            function connection:Disconnect() self.Connected = false end
            table.insert(listeners, { callback, connection })
            return connection
        end,
        Fire = function(_, ...)
            for _, listener in ipairs(listeners) do
                if listener[2].Connected then listener[1](...) end
            end
        end,
    }
end

local Color3 = { fromRGB = function(r, g, b) return { r, g, b } end }
local Vector2 = { new = function(x, y) return { X = x, Y = y } end }
local Lighting = {
    Brightness = 1, ClockTime = 20, FogEnd = 500, GlobalShadows = true,
    Ambient = "original ambient", OutdoorAmbient = "original outdoor",
}
local workspace = { Gravity = 200 }
local humanoid = {
    Health = 100, WalkSpeed = 17, JumpPower = 55, JumpHeight = 8, UseJumpPower = false,
}
function humanoid:MoveTo(position) self.LastMove = position end
local rootPart = { Position = {} }
local character = { Parent = workspace }
function character:FindFirstChild(name)
    if name == "HumanoidRootPart" then return rootPart end
end
function character:FindFirstChildOfClass(name)
    if name == "Humanoid" then return humanoid end
end
function character:WaitForChild(name)
    if name == "Humanoid" then return humanoid end
end
humanoid.Parent, rootPart.Parent = character, character
local player = { Character = character, CharacterAdded = signal(), Idled = signal() }
local teleport = { TeleportInitFailed = signal(), Teleport = function() end }
local services = {
    Lighting = Lighting,
    HttpService = { JSONEncode = function() return "{}" end },
    TeleportService = teleport,
    Players = { LocalPlayer = player },
}
local game = { PlaceId = 85920622393590, GameId = 3317771874 }
function game:GetService(name)
    assert(services[name], "Unexpected fixture service: " .. name)
    return services[name]
end

local ui = { Destroyed = false }
function ui:Update(snapshot)
    self.State = table.clone(snapshot)
end
function ui:Destroy() self.Destroyed = true end
local InterfaceStub = {}
function InterfaceStub.mount(spec)
    ui.Spec = spec
    return ui
end

local connectHook, snapshotHook, assignmentHook, collectionHook
local adapter = {
    ConnectCalls = 0, NativeCalls = 0, AssignmentCalls = 0, CollectionCalls = 0,
    Supported = { AutoFarm = false, AutoCollectOrbs = false, AutoCollectLootbags = false, WalkToTarget = false },
    Reason = "Not connected; use manual reconnect.", Report = "Fixture adapter report.",
}
function adapter:Connect(active)
    self.ConnectCalls += 1
    self.ConnectToken = active
    if active and not active() then return self end
    self.NativeCalls += 1
    if connectHook then connectHook(active) end
    if active and not active() then return self end
    self.Supported = { AutoFarm = true, AutoCollectOrbs = true, AutoCollectLootbags = true, WalkToTarget = true }
    self.Reason = "Fixture protocol probe passed; game behavior remains unverified."
    return self
end
function adapter:Snapshot(active)
    self.SnapshotToken = active
    if snapshotHook then snapshotHook(active) end
    return {
        HealthKnown = true, Pets = { "pet-b", "pet-a" },
        Candidates = {
            { id = "far", name = "Chest", area = "Spawn", health = 50, distance = 50, position = {} },
            { id = "near", name = "Coin", area = "Spawn", health = 10, distance = 10, position = {} },
        },
    }
end
function adapter:Assign(target, pets, active)
    self.AssignmentCalls += 1
    self.AssignmentToken = active
    self.LastTarget, self.LastPets = target, pets
    if assignmentHook then return assignmentHook(active) end
    if not active or active() then return #pets end
    return 0
end
function adapter:Collect(kind, radius, active)
    self.CollectionCalls += 1
    self.CollectionToken = active
    if collectionHook then return collectionHook(kind, active) end
    if not active or active() then return 1 end
    return 0
end
function adapter:Destroy() self.Destroyed = true end
local AdapterStub = { new = function() return adapter end }

local careHook
local care = { Supported = { AutoHatch = false, AutoGold = false, AutoRainbow = false },
    Reason = "Pet tools idle", Report = "Care fixture", ConnectCalls = 0, HatchCalls = 0,
    ConvertCalls = 0, MenuCalls = 0, Counts = { HatchRequests = 0, GoldRequests = 0, RainbowRequests = 0 } }
function care:Connect(active)
    self.ConnectCalls += 1
    if careHook then careHook("Connect", active) end
    if not active or active() then self.Supported = { AutoHatch = true, AutoGold = true, AutoRainbow = true } end
    return self
end
function care:Hatch(egg, mode, active)
    self.HatchCalls += 1
    if careHook then careHook("Hatch", active) end
    if active and not active() then return 0 end
    self.LastEgg, self.LastMode = egg, mode
    self.Counts.HatchRequests += 1
    return 1
end
function care:Convert(variant, species, active)
    self.ConvertCalls += 1
    if careHook then careHook("Convert", active) end
    if active and not active() then return 0 end
    self.LastVariant, self.LastSpecies = variant, species
    self.Counts[variant .. "Requests"] += 1
    return 1
end
function care:CanConvert(variant, species, active)
    return self.HasBatch ~= false and (not active or active())
end
function care:OpenMenu(kind) self.MenuCalls += 1; self.LastMenu = kind; return true end
function care:NextChoice(kind, previous)
    return if kind == "Egg" then "Starter Egg" else "cat", "Chosen from loaded directory"
end
function care:Destroy() self.Destroyed = true end
local CareStub = { new = function() return care end }
local navigationHook
local navigation = { Calls = 0, Stops = 0 }
function navigation:Approach(variant, active)
    self.Calls += 1
    self.LastVariant = variant
    if navigationHook then navigationHook(variant, active) end
    return not active or active()
end
function navigation:Stop() self.Stops += 1 end
local NavigationStub = { new = function() return navigation end }

local function contains(text, expected)
    assert(string.find(text, expected, 1, true), "Missing text '" .. expected .. "' in '" .. text .. "'")
end
'''


class RuntimeTests(unittest.TestCase):
    def run_case(self, case):
        executable = ROOT / ".tools/bin/luau"
        if not executable.is_file():
            self.skipTest("Luau CLI is not installed")
        with tempfile.TemporaryDirectory(prefix="pet-suite-runtime-") as temporary:
            directory = Path(temporary)
            sources = directory / "src"
            sources.mkdir()
            for name in ["Config.luau", "Policy.luau", "Jobs.luau", "Runtime.luau"]:
                shutil.copyfile(ROOT / "src/client" / name, sources / name)
            (sources / "Interface.luau").write_text("return InterfaceStub\n", encoding="utf-8")
            (sources / "PetSim99.luau").write_text("return AdapterStub\n", encoding="utf-8")
            (sources / "PetCare.luau").write_text("return CareStub\n", encoding="utf-8")
            (sources / "MachineNavigation.luau").write_text("return NavigationStub\n", encoding="utf-8")
            (sources / "init.client.luau").write_text(
                'local Runtime = require(script.Runtime)\n'
                'local Config = require(script.Config)\n'
                'local runtime = Runtime.new(player, {})\n'
                + case + '\nprint("RUNTIME_TEST_OK")\n',
                encoding="utf-8",
            )
            output = directory / "runtime-fixture.lua"
            output.write_text(FIXTURE + builder.build_bundle(sources), encoding="utf-8")
            result = subprocess.run([str(executable), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("RUNTIME_TEST_OK", result.stdout)

    def test_chest_cursor_assist_clicks_only_once_until_target_removed(self):
        self.run_case('''
local vectorMeta = { __sub = function(a, b)
    return { Magnitude = math.abs(a.X - b.X) }
end }
local function chest()
    local item = { Name = "Heaven Chest", Parent = workspace,
        Position = setmetatable({ X = 10 }, vectorMeta) }
    function item:IsA(kind) return kind == "BasePart" end
    function item:IsDescendantOf(other) return self.Parent == other end
    return item
end
local currentTarget = chest()
player.GetMouse = function() return { Target = currentTarget } end
local clicks = 0
mouse1click = function() clicks += 1 end
assert(runtime:Action("ArmHeavenChest"))
assert(not runtime.Ready and adapter.NativeCalls == 0)
runtime:Step()
assert(clicks == 0, "clicked before the aim countdown")
clock += 4
runtime:Step()
assert(clicks == 1, "first chest never clicked")
runtime:Step()
assert(clicks == 1, "chest was clicked again while still alive")
local old = currentTarget
currentTarget = chest()
runtime:Step()
assert(clicks == 1, "changed target was clicked before previous chest disappeared")
old.Parent = nil
runtime:Step()
assert(clicks == 2, "matching respawn was not clicked")
assert(adapter.NativeCalls == 0 and care.ConnectCalls == 0, "cursor assist loaded game APIs")
assert(runtime:Action("StopHeavenChest"))
old = currentTarget
old.Parent = nil
currentTarget = chest()
runtime:Step()
assert(clicks == 2, "stopped assist kept clicking")
runtime:Destroy()
''')

    def test_chest_cursor_assist_requires_input_capability(self):
        self.run_case('''
mouse1click = nil
local ok, message = runtime:Action("ArmHeavenChest")
assert(not ok and string.find(message, "mouse1click", 1, true))
assert(not runtime.Options.HeavenChestAssist)
runtime:Destroy()
''')

    def test_local_target_scan_runs_on_load_without_networking(self):
        self.run_case('''
assert(adapter.NativeCalls == 0 and care.ConnectCalls == 0)
assert(runtime.State.HeavenTargetCount == 0)
assert(string.find(runtime.State.HeavenScanStatus, "Workspace listing unavailable", 1, true))
runtime:Destroy()
''')

    def test_targeted_farm_selects_named_small_breakable_and_excludes_boss_chest(self):
        self.run_case('''
local function part(name, x)
    local object = { Name = name, Parent = workspace, Position = { X = x, Y = 0, Z = 0 } }
    function object:IsA(kind) return kind == "BasePart" end
    function object:IsDescendantOf(parent) return self.Parent == parent end
    return object
end
local small = part("Heaven Island Vault", 15)
local giant = part("Heaven Island Angel Chest", 12)
local coin = part("Heaven Island Coin Pile", 16)
rootPart.Position = { X = 0, Y = 0, Z = 0 }
workspace.GetDescendants = function() return { small, giant, coin } end
workspace.CurrentCamera = {
    ViewportSize = { X = 1200, Y = 800 },
    WorldToViewportPoint = function(_, position)
        return { X = position.X * 10, Y = 320, Z = 1 }, true
    end
}
local moves, clicks = {}, 0
mousemoveabs = function(x, y) table.insert(moves, {x, y}) end
mouse1click = function() clicks += 1 end
player.GetMouse = function() return { Target = if #moves == 1 then small else coin } end
isrbxactive = function() return true end
local found, report = runtime:Action("ScanHeavenTargets")
assert(found and string.find(report, "2 nearby", 1, true), report)
assert(runtime:Action("StartHeavenSweep"))
runtime:Step()
assert(#moves == 1 and clicks == 0, "targeted input did not move before clicking")
clock += 1
runtime:Step()
assert(clicks == 1, "did not click targeted breakable")
clock += 2
runtime:Step()
assert(#moves == 2 and moves[2][1] ~= moves[1][1], "did not target a second individual object")
clock += 1
runtime:Step()
assert(clicks == 2, "second breakable not clicked")
clock += 2
runtime:Step()
assert(clicks == 2, "clicked object while still cooling down")
clock += 4
runtime:Step()
assert(#moves >= 3, "cooldown should let an existing object become eligible again")
assert(adapter.NativeCalls == 0 and care.ConnectCalls == 0)
assert(runtime:Action("StopHeavenSweep"))
runtime:Destroy()
''')

    def test_b_key_toggles_heaven_farm_without_toggling_while_typing(self):
        self.run_case('''
local inputBegan = signal()
services.UserInputService = {
    InputBegan = inputBegan,
    GetFocusedTextBox = function() return nil end
}
-- Runtime attaches the InputBegan listener during construction.
-- New runtime is used here so the fixture receives the new input service.
local second = Runtime.new(player, {})
mousemoveabs = function() end
mouse1click = function() end
Enum = { KeyCode = { B = "B" } }
inputBegan:Fire({KeyCode = "B"}, false)
assert(second.Options.HeavenIslandSweep)
inputBegan:Fire({KeyCode = "B"}, false)
assert(not second.Options.HeavenIslandSweep)
inputBegan:Fire({KeyCode = "B"}, true)
assert(not second.Options.HeavenIslandSweep)
second:Destroy()
runtime:Destroy()
''')

    def test_off_target_mouse_skips_click_without_stopping_farm(self):
        self.run_case('''
local target = { Name = "Heaven Vault", Parent = workspace, Position = { X=15, Y=0, Z=0 } }
function target:IsA(k) return k == "BasePart" end
function target:IsDescendantOf(p) return self.Parent == p end
rootPart.Position = {X=0,Y=0,Z=0}
workspace.GetDescendants = function() return {target} end
workspace.CurrentCamera = {ViewportSize={X=1200,Y=800},
    WorldToViewportPoint=function() return {X=200,Y=250,Z=1},true end}
mousemoveabs = function() end
local clicks = 0
mouse1click = function() clicks += 1 end
player.GetMouse = function() return { Target=nil } end
assert(runtime:Action("StartHeavenSweep"))
runtime:Step()
clock += 1
runtime:Step()
assert(clicks == 0 and runtime.Options.HeavenIslandSweep)
assert(runtime.HeavenSweepMismatches >= 1)
runtime:Destroy()
''')

    def test_zero_detected_targets_never_emits_blind_screen_clicks(self):
        self.run_case('''
workspace.GetDescendants = function() return {} end
workspace.CurrentCamera = {
    ViewportSize = { X = 1200, Y = 800 },
    WorldToViewportPoint = function() error("no targets should be projected") end
}
local clicks = 0
mousemoveabs = function() error("no targets may be clicked") end
mouse1click = function() clicks += 1 end
assert(runtime:Action("StartHeavenSweep"))
assert(runtime.State.HeavenTargetCount == 0)
for i = 1, 5 do clock += 2; runtime:Step() end
assert(clicks == 0 and runtime.Options.HeavenIslandSweep)
runtime:Destroy()
''')

    def test_targeted_farm_requires_both_input_primitives(self):
        self.run_case('''
mousemoveabs = nil
mouse1click = function() end
local ok, err = runtime:Action("StartHeavenSweep")
assert(not ok and string.find(err, "mousemoveabs", 1, true))
assert(not runtime.Options.HeavenIslandSweep)
runtime:Destroy()
''')

    def test_startup_is_passive_until_explicit_manual_reconnect(self):
        self.run_case('''
assert(adapter.ConnectCalls == 0 and adapter.NativeCalls == 0, "startup invoked game-native discovery without manual reconnect")
assert(not runtime.Ready and not runtime.Jobs:busy("connect"))
assert(ui.State and type(ui.State.Status) == "string", "passive startup did not publish UI state")
local status = string.lower(ui.State.Status)
assert(string.find(status, "idle", 1, true) or string.find(status, "connect", 1, true), "startup status does not describe manual connection")
assert(runtime:Action("Reconnect"))
assert(adapter.ConnectCalls == 1 and adapter.NativeCalls == 1 and runtime.Ready)
runtime:Destroy()
''')

    def test_pet_tools_are_independent_of_the_coin_probe_and_start_disabled(self):
        self.run_case('''
assert(care.ConnectCalls == 0, "startup loaded pet game modules")
assert(not runtime.Options.AutoHatch and not runtime.Options.AutoGold and not runtime.Options.AutoRainbow)
assert(runtime:Action("PrepareCare"))
assert(care.ConnectCalls == 1 and not runtime.Ready)
assert(runtime:SetOption("EggName", "Starter Egg"))
assert(runtime:SetOption("AutoHatch", true))
runtime:Step()
assert(care.HatchCalls == 1 and care.LastEgg == "Starter Egg")
assert(ui.State.HatchRequests == 1)
runtime:Destroy()
assert(care.Destroyed)
''')

    def test_manual_pet_actions_dispatch_without_enabling_automatic_modes(self):
        self.run_case('''
runtime:Action("PrepareCare")
assert(runtime:SetOption("EggName", "Starter Egg"))
assert(runtime:SetOption("HatchMode", "Triple"))
assert(runtime:SetOption("ConversionSpecies", "Cat"))
assert(runtime:Action("HatchOnce"))
assert(care.LastMode == "Triple")
assert(runtime:Action("GoldOnce") and care.LastVariant == "Gold")
assert(runtime:Action("RainbowOnce") and care.LastVariant == "Rainbow")
assert(care.LastSpecies == "Cat" and care.HatchCalls == 1 and care.ConvertCalls == 2)
assert(not runtime.Options.AutoHatch and not runtime.Options.AutoGold and not runtime.Options.AutoRainbow)
assert(runtime:Action("OpenGoldMenu") and care.LastMenu == "Gold")
assert(runtime:Action("OpenRainbowMenu") and care.LastMenu == "Rainbow")
assert(runtime:Action("OpenEggMenu") and care.LastMenu == "Egg")
assert(runtime:Action("OpenInventory") and care.LastMenu == "Inventory")
runtime.State.LastError = "old error"
assert(runtime:Action("ClearError") and runtime.State.LastError == "")
runtime:Destroy()
''')

    def test_conversion_walks_first_and_path_failure_never_spends_pets(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("ConversionSpecies", "Cat")
navigationHook = function() error("machine path is blocked") end
assert(runtime:Action("GoldOnce"))
assert(navigation.Calls == 1 and care.ConvertCalls == 0, "conversion ignored failed approach")
contains(runtime.State.LastError, "machine path is blocked")
navigationHook = nil
assert(runtime:Action("GoldOnce"))
assert(navigation.Calls == 2 and navigation.LastVariant == "Gold" and care.ConvertCalls == 1)
runtime:Destroy()
''')

    def test_no_eligible_six_pet_batch_never_starts_a_machine_journey(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("ConversionSpecies", "Cat")
care.HasBatch = false
assert(runtime:Action("GoldOnce"))
assert(navigation.Calls == 0 and care.ConvertCalls == 0, "walk started without an eligible six-pet batch")
runtime:Destroy()
''')

    def test_stop_during_walk_prevents_conversion_and_pauses_farm_navigation(self):
        self.run_case('''
runtime:Action("Reconnect")
runtime:Action("PrepareCare")
runtime:SetOption("AutoFarm", true)
runtime:SetOption("WalkToTarget", true)
runtime:SetOption("ConversionSpecies", "Cat")
nativeCancelThrows = true
navigationHook = function() coroutine.yield("walking to machine") end
runtime:Action("GoldOnce")
local pending = spawned[#spawned]
runtime:Step()
assert(adapter.AssignmentCalls == 0, "farm movement competed with machine approach")
runtime:StopAll()
assert(navigation.Stops > 0)
assert(coroutine.resume(pending))
assert(care.ConvertCalls == 0, "stopped approach still consumed pets")
runtime:Destroy()
''')

    def test_machine_shortcuts_approach_then_open_and_off_mode_can_stay_manual(self):
        self.run_case('''
runtime:Action("PrepareCare")
assert(runtime:Action("GoGoldMachine"))
assert(navigation.Calls == 1 and navigation.LastVariant == "Gold" and care.MenuCalls == 0)
assert(runtime:Action("OpenRainbowMenu"))
assert(navigation.Calls == 2 and navigation.LastVariant == "Rainbow" and care.LastMenu == "Rainbow")
assert(runtime:SetOption("MachineTravelMode", "Off"))
assert(runtime:Action("OpenGoldMenu"))
assert(navigation.Calls == 2 and care.LastMenu == "Gold")
runtime:Destroy()
''')

    def test_explicit_go_action_pauses_farm_even_when_auto_travel_is_off(self):
        self.run_case('''
runtime:Action("Reconnect")
runtime:Action("PrepareCare")
runtime:SetOption("MachineTravelMode", "Off")
runtime:SetOption("AutoFarm", true)
runtime:SetOption("WalkToTarget", true)
navigationHook = function() coroutine.yield("manual machine journey") end
assert(runtime:Action("GoGoldMachine"))
runtime:Step()
assert(adapter.AssignmentCalls == 0, "explicit Go action competed with farming in Off mode")
runtime:Destroy()
''')

    def test_reloading_pet_tools_stops_native_movement_from_a_pending_journey(self):
        self.run_case('''
runtime:Action("PrepareCare")
navigationHook = function() coroutine.yield("walking") end
assert(runtime:Action("GoGoldMachine"))
local stopped = navigation.Stops
runtime:Action("PrepareCare")
assert(navigation.Stops > stopped, "canceled walk left native MoveTo running")
runtime:Destroy()
''')

    def test_catalog_buttons_apply_canonical_settings_without_spending(self):
        self.run_case('''
runtime:Action("PrepareCare")
assert(runtime:Action("NextEgg"))
assert(runtime.Options.EggName == "Starter Egg")
assert(runtime:Action("NextSpecies"))
assert(runtime.Options.ConversionSpecies == "cat")
assert(care.HatchCalls == 0 and care.ConvertCalls == 0)
runtime:Destroy()
''')

    def test_pet_preparation_and_operation_failures_stop_and_report(self):
        self.run_case('''
careHook = function() error("library unavailable") end
assert(runtime:Action("PrepareCare"))
contains(runtime.State.LastError, "library unavailable")
assert(not runtime:SetOption("AutoHatch", true))
careHook = nil
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
careHook = function(kind) if kind == "Hatch" then error("hatch rejected") end end
runtime:SetOption("AutoHatch", true)
runtime:Step()
assert(not runtime.Options.AutoHatch)
contains(runtime.State.LastError, "hatch rejected")
runtime:Destroy()
''')

    def test_pending_pet_work_blocks_manual_actions_and_preparation(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
nativeCancelThrows = true
careHook = function(kind) if kind == "Hatch" then coroutine.yield("pending") end end
assert(runtime:Action("HatchOnce"))
local pending = spawned[#spawned]
assert(not runtime:Action("GoldOnce"))
assert(not runtime:Action("PrepareCare"))
assert(care.ConnectCalls == 1 and care.ConvertCalls == 0)
assert(coroutine.resume(pending))
assert(care.Counts.HatchRequests == 0)
runtime:Destroy()
''')

    def test_respawn_cancels_pet_work_and_restores_original_movement(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("MovementEnabled", true)
runtime:SetOption("EggName", "Starter Egg")
nativeCancelThrows = true
careHook = function(kind) if kind == "Hatch" then coroutine.yield("pending") end end
runtime:Action("HatchOnce")
local pending = spawned[#spawned]
local replacement = { Parent = workspace, WaitForChild = function() return nil end,
    FindFirstChild = function() return nil end }
player.Character = replacement
player.CharacterAdded:Fire(replacement)
assert(humanoid.WalkSpeed == 17)
assert(coroutine.resume(pending))
assert(care.Counts.HatchRequests == 0)
runtime:Destroy()
''')

    def test_clipboard_and_rejoin_failures_are_visible_and_recoverable(self):
        self.run_case('''
setclipboard = function() error("clipboard denied") end
assert(not runtime:Action("CopyDiagnostics"))
contains(runtime.State.LastError, "Clipboard failed")
local copied
setclipboard = function(value) copied = value end
assert(runtime:Action("CopyDiagnostics"))
contains(copied, Config.Name)
contains(copied, "Care fixture")
runtime:SetOption("Fullbright", true)
teleport.Teleport = function() error("teleport rejected") end
assert(not runtime:Action("Rejoin"))
assert(not runtime.Options.Fullbright and Lighting.Brightness == 1)
runtime:Destroy()
''')

    def test_stop_all_cancels_pending_pet_mutation_without_replaying_or_overlapping(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
nativeCancelThrows = true
careHook = function(kind, active)
    if kind == "Hatch" then coroutine.yield("pending hatch") end
end
runtime:SetOption("AutoHatch", true)
runtime:Step()
assert(care.HatchCalls == 1)
local pending = spawned[#spawned]
runtime:StopAll()
runtime:SetOption("AutoHatch", true)
runtime:Step()
assert(care.HatchCalls == 1, "pending care request overlapped")
assert(coroutine.resume(pending))
assert(care.Counts.HatchRequests == 0, "canceled hatch published a late result")
runtime:Destroy()
''')

    def test_slow_conversions_cannot_starve_hatching_or_other_conversion_stage(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
runtime:SetOption("ConversionSpecies", "Cat")
for _, key in ipairs({"AutoHatch", "AutoGold", "AutoRainbow"}) do runtime:SetOption(key, true) end
local order = {}
careHook = function(kind, active)
    if kind ~= "Connect" then table.insert(order, kind); coroutine.yield("slow pet operation") end
end
for _ = 1, 3 do
    runtime:Step()
    local worker = spawned[#spawned]
    clock += 5
    assert(coroutine.resume(worker))
end
assert(care.ConvertCalls == 2 and care.HatchCalls == 1, "one slow pet feature starved the other stages")
runtime:Destroy()
''')

    def test_connect_receives_the_cooperative_job_token(self):
        self.run_case('''
assert(runtime:Action("Reconnect"))
assert(type(adapter.ConnectToken) == "function", "Connect did not receive its active-job token")
runtime:Destroy()
''')

    def test_snapshot_receives_the_cooperative_job_token(self):
        self.run_case('''
runtime:Action("Reconnect")
assert(runtime:SetOption("AutoFarm", true))
runtime:Step()
assert(type(adapter.SnapshotToken) == "function", "Snapshot did not receive its active-job token")
assert(adapter.LastTarget.id == "near" and #adapter.LastPets == 2)
runtime:Destroy()
''')

    def test_timed_out_assignment_cannot_send_late_requests_or_overlap_a_replacement(self):
        self.run_case('''
runtime:Action("Reconnect")
nativeCancelThrows = true
local dispatches = 0
assignmentHook = function(active)
    dispatches += 1
    coroutine.yield("native assignment still pending")
    if active() then dispatches += 1 end
    return dispatches
end
runtime:SetOption("AutoFarm", true)
runtime:Step()
local worker = runtime.Jobs.slots.AutoFarm.thread
assert(dispatches == 1 and coroutine.status(worker) == "suspended")
clock += Config.FarmTimeout
runtime.Jobs:tick()
assert(runtime.Jobs:blocked("AutoFarm"), "failed cancellation released an in-flight slot")
clock += 10
runtime:Step()
assert(adapter.AssignmentCalls == 1, "replacement overlapped the timed-out assignment")
local ok, reason = coroutine.resume(worker)
assert(ok, reason)
assert(dispatches == 1, "canceled assignment sent another request after native cancellation failed")
assert(not runtime.Jobs:busy("AutoFarm"), "exited canceled worker kept its slot reserved")
runtime:Destroy()
''')

    def test_canceled_collection_stays_canceled_after_the_toggle_is_reenabled(self):
        for feature, kind in [("AutoCollectOrbs", "orbs"), ("AutoCollectLootbags", "lootbags")]:
            with self.subTest(feature=feature):
                self.run_case('''
runtime:Action("Reconnect")
nativeCancelThrows = true
local dispatches = 0
collectionHook = function(kind, active)
    assert(kind == "''' + kind + '''")
    dispatches += 1
    coroutine.yield("collection still pending")
    if active() then dispatches += 1 end
    return dispatches
end
runtime:SetOption("''' + feature + '''", true)
runtime:Step()
local worker = runtime.Jobs.slots["''' + feature + '''"].thread
runtime:SetOption("''' + feature + '''", false)
runtime:SetOption("''' + feature + '''", true)
assert(runtime.Jobs:blocked("''' + feature + '''"))
local ok, reason = coroutine.resume(worker)
assert(ok, reason)
assert(dispatches == 1, "old collection token became active again after reenable")
assert(adapter.CollectionCalls == 1)
runtime:Destroy()
''')

    def test_canceled_connect_cannot_publish_late_capabilities_or_ready_state(self):
        self.run_case('''
nativeCancelThrows = true
connectHook = function(active)
    coroutine.yield("native module require still pending")
end
runtime:Action("Reconnect")
local worker = runtime.Jobs.slots.connect.thread
runtime:StopAll()
local ok, reason = coroutine.resume(worker)
assert(ok, reason)
assert(not runtime.Ready, "canceled probe reenabled Runtime.Ready")
assert(not adapter.Supported.AutoFarm, "canceled probe restored stale adapter capabilities")
runtime:Destroy()
''')

    def test_tick_exception_is_handled_without_killing_the_pulse(self):
        self.run_case('''
runtime:Action("Reconnect")
runtime:SetOption("AutoFarm", true)
runtime.Jobs.tick = function() error("fixture scheduler failure") end
local ok, reason = coroutine.resume(runtime.Pulse)
assert(ok, "Jobs.tick exception escaped the pulse: " .. tostring(reason))
assert(coroutine.status(runtime.Pulse) == "suspended", "pulse died on scheduler failure")
contains(runtime.State.LastError, "fixture scheduler failure")
assert(not runtime.Options.AutoFarm and not runtime.Options.AutoCollectOrbs and not runtime.Options.AutoCollectLootbags)
runtime:Destroy()
''')

    def test_stop_all_restores_movement_lighting_and_canonical_options(self):
        self.run_case('''
assert(runtime:SetOption("Radius", 5000))
assert(runtime.Options.Radius == 1000 and ui.State.Options.Radius == 1000)
assert(runtime:SetOption("MovementEnabled", true))
assert(humanoid.WalkSpeed == Config.Options.WalkSpeed and humanoid.JumpHeight == 6.25)
assert(runtime:SetOption("Fullbright", true))
assert(Lighting.ClockTime == 14 and not Lighting.GlobalShadows)
runtime:StopAll()
assert(humanoid.WalkSpeed == 17 and humanoid.JumpPower == 55 and humanoid.JumpHeight == 8)
assert(Lighting.ClockTime == 20 and Lighting.GlobalShadows)
assert(Lighting.Ambient == "original ambient" and Lighting.OutdoorAmbient == "original outdoor")
for _, value in pairs(runtime.Options) do
    if type(value) == "boolean" then assert(not value) end
end
runtime:Destroy()
runtime:Destroy()
assert(ui.Destroyed)
for _, connection in ipairs(runtime.Connections) do assert(not connection.Connected) end
''')


if __name__ == "__main__":
    unittest.main()
