"""Run real scheduler, pet care and walking together at explicit game boundaries."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_care_fixture", ROOT / "tests/test_care.py")
care_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(care_tests)
builder = care_tests.builder
FIXTURE = care_tests.FIXTURE + r'''
local function signal()
    return { Connect = function(_, callback)
        return { Disconnect = function() end }
    end }
end
player.CharacterAdded, player.Idled = signal(), signal()
local humanoid = instance("Humanoid", "Humanoid", character)
humanoid.Health, humanoid.WalkSpeed, humanoid.JumpPower, humanoid.JumpHeight = 100, 16, 50, 7
humanoid.UseJumpPower = true
function character:FindFirstChildOfClass(class)
    if class == "Humanoid" then return humanoid end
end
function humanoid:MoveTo(position) rootPart.Position = position end
function task.spawn(callback)
    local thread = coroutine.create(callback)
    local ok, message = coroutine.resume(thread)
    assert(ok, tostring(message))
    return thread
end
function task.cancel(thread) coroutine.close(thread) end
function task.wait() return coroutine.yield("waiting") end
local Enum = { PathStatus = { Success = "Success" }, PathWaypointAction = { Walk = "Walk", Jump = "Jump" } }
local Color3 = { fromRGB = function(r,g,b) return { r,g,b } end }
local Lighting = { Brightness=1, ClockTime=12, FogEnd=100, GlobalShadows=true, Ambient={}, OutdoorAmbient={} }
local map = instance("__MAP", "Folder", workspace)
local interactive = instance("Interactive", "Folder", map)
local gold = instance("Gold Machine", "Model", interactive)
local goldPad = part("Pad", Vector3.new(40,0,0), gold)
local rainbow = instance("Rainbow Machine", "Model", interactive)
local rainbowPad = part("Pad", Vector3.new(80,0,0), rainbow)
local computeHook
local pathService = {}
function pathService:CreatePath()
    local path = { Status = Enum.PathStatus.Success }
    function path:ComputeAsync(start, finish)
        self.Finish = finish
        if computeHook then computeHook() end
    end
    function path:GetWaypoints() return { { Position=self.Finish, Action=Enum.PathWaypointAction.Walk } } end
    return path
end
local nativeService = game.GetService
function game:GetService(name)
    if name == "Lighting" then return Lighting end
    if name == "HttpService" then return { JSONEncode=function() return "{}" end } end
    if name == "TeleportService" then return { TeleportInitFailed=signal() } end
    if name == "PathfindingService" then return pathService end
    return nativeService(self, name)
end
local ui = { Update=function() end, Destroy=function() end }
local InterfaceStub = { mount=function() return ui end }
'''


class PetWorkflowTests(unittest.TestCase):
    def run_case(self, case):
        with tempfile.TemporaryDirectory(prefix="psx-workflow-") as temporary:
            root = Path(temporary)
            sources = root / "src"
            sources.mkdir()
            for source in (ROOT / "src/client").glob("*.luau"):
                if source.name not in {"init.client.luau", "Interface.luau"}:
                    shutil.copyfile(source, sources / source.name)
            (sources / "Interface.luau").write_text("return InterfaceStub\n")
            (sources / "init.client.luau").write_text(
                'local Runtime = require(script.Runtime)\nlocal runtime = Runtime.new(player, playerGui)\n'
                + case + '\nruntime:Destroy()\nprint("WORKFLOW_OK")\n')
            output = root / "workflow.lua"
            output.write_text(FIXTURE + builder.build_bundle(sources))
            result = subprocess.run([str(ROOT / ".tools/bin/luau"), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("WORKFLOW_OK", result.stdout)

    def test_real_egg_and_conversion_handlers_approach_before_boundary_requests(self):
        self.run_case('''
assert(#calls == 0 and nativeCalls == 0)
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
runtime:SetOption("ConversionSpecies", "Cat")
careHook = function(command)
    local destination = if command == "Buy Egg" then eggModel:FindFirstChild("Center").Position
        elseif command == "Use Golden Machine" then goldPad.Position else rainbowPad.Position
    assert((rootPart.Position - destination).Magnitude <= 8, "request sent before arrival")
    return true
end
assert(runtime:Action("HatchOnce"))
assert(runtime:Action("GoldOnce"))
assert(runtime:Action("RainbowOnce"))
assert(#calls == 3 and calls[1].command == "Buy Egg" and calls[2].command == "Use Golden Machine"
    and calls[3].command == "Use Rainbow Machine")
assert(runtime.Care.Counts.HatchRequests == 1 and runtime.Care.Counts.GoldRequests == 1
    and runtime.Care.Counts.RainbowRequests == 1)
''')

    def test_real_auto_hatch_waits_for_funds_then_walks_and_submits(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
save.Coins = 0
runtime:SetOption("AutoHatch", true)
runtime:Step()
assert(#calls == 0 and runtime.Options.AutoHatch)
save.Coins = 1000
now += 4
runtime:Step()
assert(#calls == 1 and calls[1].command == "Buy Egg")
assert((rootPart.Position - eggModel:FindFirstChild("Center").Position).Magnitude <= 8)
''')

    def test_death_during_real_pathfinding_prevents_purchase(self):
        self.run_case('''
runtime:Action("PrepareCare")
runtime:SetOption("EggName", "Starter Egg")
computeHook = function() humanoid.Health = 0 end
runtime:Action("HatchOnce")
assert(#calls == 0 and runtime.Care.Counts.HatchRequests == 0)
''')
