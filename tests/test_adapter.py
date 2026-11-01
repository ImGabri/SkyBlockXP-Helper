"""Execute the real adapter against explicit Roblox-boundary fixtures.

These tests validate failure gates and protocol dispatch, not live Classic Event
compatibility or whether any game action succeeded on a server.
"""

import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("adapter_test_builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


FIXTURE = r'''
local realTypeof = typeof
local function typeof(value)
    if type(value) == "table" and value._kind == "Vector3" then return "Vector3" end
    return realTypeof(value)
end
local vectorMetatable = {}
local Vector3 = {}
function Vector3.new(x, y, z)
    return setmetatable({ X = x, Y = y, Z = z, _kind = "Vector3" }, vectorMetatable)
end
vectorMetatable.__sub = function(a, b)
    return Vector3.new(a.X - b.X, a.Y - b.Y, a.Z - b.Z)
end
vectorMetatable.__index = function(value, key)
    if key == "Magnitude" then return math.sqrt(value.X^2 + value.Y^2 + value.Z^2) end
end
local now = 100
local os = { clock = function() return now end }
local task = { wait = function() end }

local function instance(name, className, parent)
    local object = { Name = name, ClassName = className, Parent = parent, Children = {}, Attributes = {} }
    function object:IsA(class)
        return self.ClassName == class or (class == "BasePart" and self.ClassName == "Part")
    end
    function object:GetChildren() return table.clone(self.Children) end
    function object:FindFirstChild(name)
        for _, child in ipairs(self.Children) do
            if child.Name == name then return child end
        end
        return nil
    end
    function object:FindFirstChildWhichIsA(class, recursive)
        for _, child in ipairs(self.Children) do
            if child:IsA(class) then return child end
            if recursive then
                local nested = child:FindFirstChildWhichIsA(class, true)
                if nested then return nested end
            end
        end
        return nil
    end
    function object:GetAttribute(name) return self.Attributes[name] end
    if parent then table.insert(parent.Children, object) end
    return object
end
local function part(name, position, parent)
    local object = instance(name, "Part", parent)
    object.Position = position
    return object
end
local workspace = instance("Workspace", "Workspace")
local things = instance("__THINGS", "Folder", workspace)
local coins = instance("Coins", "Folder", things)
local orbs = instance("Orbs", "Folder", things)
local lootbags = instance("Lootbags", "Folder", things)
local storage = instance("ReplicatedStorage", "ReplicatedStorage")
local library = instance("Library", "Folder", storage)
local client = instance("Client", "Folder", library)
local networkModule = instance("Network", "ModuleScript", client)
local petsModule = instance("PetCmds", "ModuleScript", client)
local character = instance("Character", "Model", workspace)
local rootPart = part("HumanoidRootPart", Vector3.new(0, 0, 0), character)
local player = { Character = character }
local game = { PlaceId = 85920622393590, GameId = 3317771874 }
function game:GetService(name)
    if name == "ReplicatedStorage" then return storage end
    if name == "Players" then return { LocalPlayer = player } end
    error("Unexpected service: " .. name)
end
local loadedCoin = instance("coin1", "Model", coins)
part("Coin", Vector3.new(10, 0, 0), loadedCoin)
local records = {
    coin1 = { p = Vector3.new(10, 0, 0), a = "Spawn", n = "Coin Pile", health = 30, pets = {} },
}
local equipped = { { uid = "pet-a" }, { uid = "pet-b" } }
local calls = {}
local nativeCalls = 0
local denyRequire = false
local invokeHook, fireHook
local network = {}
function network.Invoke(command, ...)
    table.insert(calls, { method = "Invoke", command = command, args = table.pack(...) })
    if invokeHook then
        local result = invokeHook(command, ...)
        if result ~= nil then return result end
    end
    if command == "Get Coins" then return records end
    if command == "Join Coin" then return true end
    error("Unexpected Invoke command: " .. command)
end
function network.Fire(command, ...)
    table.insert(calls, { method = "Fire", command = command, args = table.pack(...) })
    if fireHook then
        local result = fireHook(command, ...)
        if result ~= nil then return result end
    end
    return nil
end
local exports = {
    [networkModule] = network,
    [petsModule] = { GetEquipped = function() return equipped end },
}
local function require(module)
    nativeCalls += 1
    if denyRequire then error("Fixture denied native module access") end
    assert(module and module:IsA("ModuleScript"), "Unexpected native require target")
    return exports[module]
end
local function contains(text, expected)
    assert(string.find(text, expected, 1, true), "Missing text '" .. expected .. "' in '" .. text .. "'")
end
local function assertBlocked(adapter)
    for key, supported in pairs(adapter.Supported) do assert(not supported, key .. " should be blocked") end
end
'''


class AdapterTests(unittest.TestCase):
    def run_case(self, case):
        executable = ROOT / ".tools/bin/luau"
        if not executable.is_file():
            self.skipTest("Luau CLI is not installed")
        with tempfile.TemporaryDirectory(prefix="pet-suite-adapter-") as temporary:
            directory = Path(temporary)
            sources = directory / "src"
            sources.mkdir()
            for name in ["Config.luau", "PetSim99.luau", "Jobs.luau"]:
                shutil.copyfile(ROOT / "src/client" / name, sources / name)
            (sources / "init.client.luau").write_text(
                'local PetSim99 = require(script.PetSim99)\n' + case + '\nprint("ADAPTER_TEST_OK")\n',
                encoding="utf-8",
            )
            output = directory / "adapter-fixture.lua"
            output.write_text(FIXTURE + builder.build_bundle(sources), encoding="utf-8")
            result = subprocess.run([str(executable), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("ADAPTER_TEST_OK", result.stdout)

    def test_wrong_place_or_universe_makes_no_native_or_network_calls(self):
        for change in ["game.PlaceId = 1", "game.GameId = 1"]:
            with self.subTest(change=change):
                self.run_case(change + '''
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
assert(nativeCalls == 0 and #calls == 0)
contains(adapter.Reason, "Current destination differs")
''')

    def test_native_require_denial_leaves_all_features_blocked(self):
        self.run_case('''
denyRequire = true
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
assert(nativeCalls == 1 and #calls == 0)
contains(adapter.Reason, "Native require")
contains(adapter.Reason, "Fixture denied native module access")
''')

    def test_network_call_preserves_tuple_slots_and_return_count(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
network.Invoke = function(command)
    if command == "Tuple Fixture" then return "head", nil, false, 7, nil end
    if command == "Empty Fixture" then return end
    error("Unexpected fixture command")
end
local values = table.pack(adapter:_call("Invoke", "Tuple Fixture"))
assert(values.n == 5, "network call discarded tuple return slots")
assert(values[1] == "head" and values[2] == nil and values[3] == false and values[4] == 7 and values[5] == nil)
assert(table.pack(adapter:_call("Invoke", "Empty Fixture")).n == 0, "empty response was converted into one nil return")
''')

    def test_true_status_plus_valid_coin_dictionary_unlocks_probe(self):
        self.run_case('''
local invoke = network.Invoke
network.Invoke = function(command, ...)
    local result = invoke(command, ...)
    if command == "Get Coins" then return true, result end
    return result
end
local adapter = PetSim99.new():Connect()
assert(adapter.Supported.AutoFarm, adapter.Reason)
local snapshot = adapter:Snapshot()
assert(#snapshot.Candidates == 1 and snapshot.Candidates[1].id == "coin1")
assert(#snapshot.Pets == 2 and snapshot.HealthKnown)
assert(#calls == 2 and calls[1].command == "Get Coins" and calls[2].command == "Get Coins")
''')

    def test_true_status_does_not_bypass_coin_schema_validation(self):
        self.run_case('''
network.Invoke = function(command)
    assert(command == "Get Coins")
    return true, { coin1 = { p=Vector3.new(10,0,0), a="Spawn", n="Coin", health="not-a-number" } }
end
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "unknown coin schema")
''')

    def test_unsupported_coin_tuples_report_return_count_and_types(self):
        cases = [
            ("return", 0, "none"),
            ("return nil", 1, "nil"),
            ('return "private fixture payload"', 1, "string"),
            ("return true", 1, "boolean"),
            ("return nil, records", 2, "nil,table"),
            ('return true, records, "extra"', 3, "boolean,table,string"),
        ]
        for response, count, types in cases:
            with self.subTest(response=response):
                self.run_case('''
network.Invoke = function(command)
    assert(command == "Get Coins")
    ''' + response + '''
end
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "returns=''' + str(count) + '''")
contains(adapter.Reason, "types=''' + types + '''")
assert(not string.find(adapter.Reason, "private fixture payload", 1, true), "diagnostics exposed response contents")
''')

    def test_false_status_with_coin_payload_is_explicitly_rejected(self):
        self.run_case('''
network.Invoke = function(command)
    assert(command == "Get Coins")
    return false, records
end
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "explicitly rejected")
''')

    def test_coin_dictionary_with_extra_returns_is_rejected(self):
        for extra in ["false", '"extra"']:
            with self.subTest(extra=extra):
                self.run_case('''
local invoke = network.Invoke
network.Invoke = function(command, ...)
    local result = invoke(command, ...)
    if command == "Get Coins" then return result, ''' + extra + ''' end
    return result
end
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "returns=2")
''')

    def test_empty_malformed_and_wrapped_coin_records_are_rejected(self):
        for replacement in [
            "7", "{}", "{ data = records }",
            '{ coin1 = { p = {X=10,Y=0,Z=0}, a="Spawn", n="Coin" } }',
            '{ coin1 = { p = Vector3.new(10,0,0), a="Spawn", n="Coin", health="30" } }',
            '{ coin1 = { p = Vector3.new(0/0,0,0), a="Spawn", n="Coin" } }',
        ]:
            with self.subTest(records=replacement):
                self.run_case(f"records = {replacement}\n" + '''
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
assert(#calls == 1 and calls[1].command == "Get Coins")
''')

    def test_unloaded_or_wrong_class_coin_models_cannot_unlock_farming(self):
        self.run_case('''
loadedCoin.ClassName = "Folder"
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "No valid Get Coins record")
''')

    def test_invalid_equipped_pet_shape_is_rejected(self):
        self.run_case('''
equipped = { "pet-a" }
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "unknown pet record")
''')

    def test_valid_loaded_records_normalize_candidates_and_duplicate_uids(self):
        self.run_case('''
equipped = { {uid=17}, {uid="17"}, {uid="pet-b"} }
records.unloaded = { p=Vector3.new(50,0,0), a="Other", n="Unloaded", health=99 }
local adapter = PetSim99.new():Connect()
assert(adapter.Supported.AutoFarm and adapter.Supported.WalkToTarget)
assert(adapter.Supported.AutoCollectOrbs and adapter.Supported.AutoCollectLootbags)
local snapshot = adapter:Snapshot()
assert(#snapshot.Candidates == 1 and #snapshot.Pets == 2 and snapshot.HealthKnown)
local target = snapshot.Candidates[1]
assert(target.id == "coin1" and target.name == "Coin Pile" and target.area == "Spawn")
assert(target.distance == 10 and target.health == 30 and target.healthKnown)
assert(target.instance == loadedCoin and typeof(target.position) == "Vector3")
local uids = {}
for _, uid in ipairs(snapshot.Pets) do uids[tostring(uid)] = true end
assert(uids["17"] and uids["pet-b"])
contains(adapter.Reason, "still unverified in game")
''')

    def test_missing_health_does_not_claim_health_priority_support(self):
        self.run_case('''
records.coin1.health = nil
local adapter = PetSim99.new():Connect()
assert(adapter.Supported.AutoFarm)
local snapshot = adapter:Snapshot()
assert(not snapshot.HealthKnown and not snapshot.Candidates[1].healthKnown)
''')

    def test_world_area_rejection_blocks_unavailable_loaded_targets(self):
        self.run_case('''
local worldModule = instance("WorldCmds", "ModuleScript", client)
exports[worldModule] = { HasArea = function() return false end }
local adapter = PetSim99.new():Connect()
assertBlocked(adapter)
contains(adapter.Reason, "No valid Get Coins record")
''')

    def test_assignment_joins_then_farms_each_unique_unassigned_pet(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
calls = {}
assert(adapter:Assign(snapshot.Candidates[1], {"pet-a", "pet-a", "pet-b"}, function() return true end) == 2)
assert(#calls == 4)
for offset, uid in ipairs({"pet-a", "pet-b"}) do
    local join, farm = calls[offset*2-1], calls[offset*2]
    assert(join.method == "Invoke" and join.command == "Join Coin")
    assert(join.args.n == 2 and join.args[1] == "coin1" and #join.args[2] == 1 and join.args[2][1] == uid)
    assert(farm.method == "Fire" and farm.command == "Farm Coin")
    assert(farm.args.n == 2 and farm.args[1] == "coin1" and farm.args[2] == uid)
end
contains(adapter.Report, "2 pet farm dispatches")
''')

    def test_existing_server_assignments_are_not_dispatched_again(self):
        self.run_case('''
records.coin1.pets = {"pet-a"}
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
calls = {}
assert(adapter:Assign(snapshot.Candidates[1], snapshot.Pets) == 1)
assert(#calls == 2 and calls[1].args[2][1] == "pet-b")
''')

    def test_cancellation_before_join_or_between_join_and_farm_stops_requests(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
calls = {}
assert(adapter:Assign(snapshot.Candidates[1], snapshot.Pets, function() return false end) == 0)
assert(#calls == 0)
local running = true
invokeHook = function(command) if command == "Join Coin" then running = false end end
assert(adapter:Assign(snapshot.Candidates[1], snapshot.Pets, function() return running end) == 0)
assert(#calls == 1 and calls[1].command == "Join Coin")
''')

    def test_timeout_keeps_uncancellable_worker_busy_and_prevents_further_dispatch(self):
        self.run_case('''
local Jobs = require(script.Jobs)
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
calls = {}
local threads, reports = {}, 0
local jobs = Jobs.new({
    clock = function() return now end,
    spawn = function(fn)
        local thread = coroutine.create(fn)
        table.insert(threads, thread)
        return thread
    end,
    cancel = function() error("fixture native worker cannot be canceled") end,
})
local yielded = false
invokeHook = function(command)
    if command == "Join Coin" and not yielded then
        yielded = true
        coroutine.yield("pending native request")
    end
end
assert(jobs:start("farm", 1, function(activeJob)
    -- The fallback makes the old implementation fail because of stale work,
    -- rather than a fixture error from its missing cooperative token argument.
    activeJob = activeJob or function() return true end
    return adapter:Assign(snapshot.Candidates[1], snapshot.Pets, activeJob)
end, function(ok)
    assert(not ok, "only the timeout should publish a result")
    reports += 1
end))
assert(coroutine.resume(threads[1]))
assert(#calls == 1 and calls[1].command == "Join Coin")
now += 2
jobs:tick()
assert(reports == 1, "timeout should report exactly once")
assert(jobs:busy("farm"), "failed cancellation freed a still-running worker slot")
assert(not jobs:start("farm", 1, function() error("overlapping worker") end, function() end),
    "replacement worker overlapped an uncancellable native request")
local ok, message = coroutine.resume(threads[1])
assert(ok, message)
assert(#calls == 1, "timed-out worker sent Farm Coin or a subsequent Join Coin")
assert(not jobs:busy("farm"), "finished canceled worker did not release its slot")
jobs:tick()
assert(reports == 1, "old worker or repeated tick published a second result")
assert(jobs:start("farm", 1, function() return 0 end, function() end),
    "finished worker permanently blocked a fresh request")
''')

    def test_explicit_join_rejection_blocks_features_without_farm_dispatch(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
calls = {}
invokeHook = function(command) if command == "Join Coin" then return false end end
local ok, message = pcall(adapter.Assign, adapter, snapshot.Candidates[1], snapshot.Pets)
assert(not ok)
contains(message, "explicitly rejected")
assertBlocked(adapter)
assert(#calls == 1 and calls[1].command == "Join Coin")
''')

    def test_changed_snapshot_schema_disables_a_previously_connected_adapter(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
assert(adapter.Supported.AutoFarm)
records = { data = {} }
local ok = pcall(adapter.Snapshot, adapter)
assert(not ok)
assertBlocked(adapter)
''')

    def test_orb_collection_caps_count_and_radius_and_skips_collected_objects(self):
        self.run_case('''
part("far", Vector3.new(31,0,0), orbs)
local claimed = part("claimed", Vector3.new(1,0,0), orbs)
claimed.Attributes.Collected = true
for index=1,25 do part("orb-" .. index, Vector3.new(5,0,0), orbs) end
local adapter = PetSim99.new():Connect()
calls = {}
assert(adapter:Collect("orbs", 999) == 20)
assert(#calls == 1 and calls[1].method == "Fire" and calls[1].command == "Claim Orbs")
local ids = calls[1].args[1]
assert(#ids == 20)
for _, id in ipairs(ids) do assert(id ~= "far" and id ~= "claimed") end
contains(adapter.Report, "20 orb IDs")
''')

    def test_pickup_cooldown_expires_after_two_seconds(self):
        self.run_case('''
part("orb-a", Vector3.new(2,0,0), orbs)
local adapter = PetSim99.new():Connect()
calls = {}
assert(adapter:Collect("orbs", 30) == 1)
assert(adapter:Collect("orbs", 30) == 0)
now += 1.99
assert(adapter:Collect("orbs", 30) == 0)
now += 0.02
assert(adapter:Collect("orbs", 30) == 1)
assert(#calls == 2)
''')

    def test_lootbag_dispatch_has_four_item_cap_and_exact_position_argument(self):
        self.run_case('''
part("far", Vector3.new(100,0,0), lootbags)
for index=1,6 do part("bag-" .. index, Vector3.new(3,0,0), lootbags) end
local adapter = PetSim99.new():Connect()
calls = {}
assert(adapter:Collect("lootbags", 30) == 4)
assert(#calls == 4)
for _, call in ipairs(calls) do
    assert(call.method == "Fire" and call.command == "Collect Lootbag")
    assert(call.args.n == 2 and call.args[1] ~= "far" and call.args[2] == rootPart.Position)
end
''')

    def test_lootbag_cancellation_stops_after_first_dispatch(self):
        self.run_case('''
for index=1,4 do part("bag-" .. index, Vector3.new(3,0,0), lootbags) end
local adapter = PetSim99.new():Connect()
calls = {}
local running = true
fireHook = function(command) if command == "Collect Lootbag" then running = false end end
assert(adapter:Collect("lootbags", 30, function() return running end) == 1)
assert(#calls == 1)
''')

    def test_destroy_blocks_all_further_dispatch(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
adapter:Destroy()
calls = {}
assertBlocked(adapter)
assert(not pcall(adapter.Snapshot, adapter))
assert(not pcall(adapter.Assign, adapter, snapshot.Candidates[1], snapshot.Pets))
assert(not pcall(adapter.Collect, adapter, "orbs", 30))
assert(#calls == 0)
''')

    def test_late_snapshot_failure_cannot_disable_a_new_connection(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
invokeHook = function(command)
    if command == "Get Coins" then
        invokeHook = nil
        adapter:Connect()
        error("old snapshot request failed after reconnect")
    end
end
assert(not pcall(adapter.Snapshot, adapter))
assert(adapter.Supported.AutoFarm, "old snapshot disabled the newer connection")
''')

    def test_late_coin_reply_cannot_overwrite_new_connection_response_metadata(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
local invoke = network.Invoke
local oldRequestPending = true
network.Invoke = function(command, ...)
    if command == "Get Coins" and oldRequestPending then
        oldRequestPending = false
        adapter:Connect()
        return nil
    end
    return invoke(command, ...)
end
assert(not pcall(adapter.Snapshot, adapter), "old snapshot should be canceled after reconnect")
assert(adapter.Supported.AutoFarm, "old reply disabled the newer connection")
contains(adapter._coinResponse, "returns=1")
contains(adapter._coinResponse, "types=table")
''')

    def test_late_assignment_failure_cannot_disable_a_new_connection(self):
        self.run_case('''
local adapter = PetSim99.new():Connect()
local snapshot = adapter:Snapshot()
invokeHook = function(command)
    if command == "Join Coin" then
        invokeHook = nil
        adapter:Connect()
        error("old assignment request failed after reconnect")
    end
end
local ok, count = pcall(adapter.Assign, adapter, snapshot.Candidates[1], snapshot.Pets)
assert(ok and count == 0, "stale assignment should cancel without publishing an error")
assert(adapter.Supported.AutoFarm, "old assignment disabled the newer connection")
''')

    def test_late_pickup_failure_cannot_disable_a_new_connection(self):
        self.run_case('''
part("orb-a", Vector3.new(2,0,0), orbs)
local adapter = PetSim99.new():Connect()
fireHook = function(command)
    if command == "Claim Orbs" then
        fireHook = nil
        adapter:Connect()
        error("old pickup request failed after reconnect")
    end
end
local ok, count = pcall(adapter.Collect, adapter, "orbs", 30)
assert(ok and count == 0, "stale pickup should cancel without publishing an error")
assert(adapter.Supported.AutoFarm, "old pickup disabled the newer connection")
''')


if __name__ == "__main__":
    unittest.main()
