"""Run actual machine walking against explicit pathfinding/character fixtures."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("navigation_builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

FIXTURE = r'''
local realTypeof = typeof
local function typeof(value)
    if type(value) == "table" and type(value.ClassName) == "string" and type(value.IsA) == "function" then return "Instance" end
    return if type(value) == "table" and value.kind == "Vector3" then "Vector3" else realTypeof(value)
end
local vectorMeta = {}
local Vector3 = {}
function Vector3.new(x,y,z) return setmetatable({X=x,Y=y,Z=z,kind="Vector3"},vectorMeta) end
vectorMeta.__sub = function(a,b) return Vector3.new(a.X-b.X,a.Y-b.Y,a.Z-b.Z) end
vectorMeta.__index = function(value,key)
    if key == "Magnitude" then return math.sqrt(value.X^2+value.Y^2+value.Z^2) end
end
local function instance(name,class,parent)
    local object = {Name=name,ClassName=class,Parent=parent,Children={}}
    function object:IsA(kind) return self.ClassName==kind or (kind=="BasePart" and self.ClassName=="Part") end
    function object:FindFirstChild(key)
        for _, item in ipairs(self.Children) do if item.Name==key then return item end end
    end
    function object:FindFirstChildOfClass(kind)
        for _, item in ipairs(self.Children) do if item:IsA(kind) then return item end end
    end
    function object:IsDescendantOf(ancestor)
        local current = self.Parent
        while current do
            if current == ancestor then return true end
            current = current.Parent
        end
        return false
    end
    if parent then table.insert(parent.Children,object) end
    return object
end
local workspace=instance("Workspace","Workspace")
local map=instance("__MAP","Folder",workspace)
local interactive=instance("Interactive","Folder",map)
local gold=instance("Gold Machine","Model",interactive)
local goldPad=instance("Pad","Part",gold)
goldPad.Position=Vector3.new(40,0,0)
local rainbow=instance("Rainbow Machine","Model",interactive)
local rainbowPad=instance("Pad","Part",rainbow)
rainbowPad.Position=Vector3.new(80,0,0)
local eggs=instance("Eggs","Folder",map)
local egg=instance("Starter Egg","Model",eggs)
local eggCenter=instance("Center","Part",egg)
eggCenter.Position=Vector3.new(120,0,0)
local character=instance("Character","Model",workspace)
local root=instance("HumanoidRootPart","Part",character)
root.Position=Vector3.new(0,0,0)
local humanoid=instance("Humanoid","Humanoid",character)
humanoid.Health=100
humanoid.WalkSpeed=16
local player={Character=character}
local moves, progress={},{}
local autoMove=true
function humanoid:MoveTo(position)
    table.insert(moves,position)
    if autoMove then root.Position=position end
end
local Enum={PathStatus={Success="Success",NoPath="NoPath"},PathWaypointAction={Walk="Walk",Jump="Jump"}}
local now=100
local os={clock=function() return now end}
local waitHook,computeHook
local task={wait=function(delta)
    now+=delta or 0.1
    if waitHook then waitHook() end
end}
local pathCalls=0
local pathStatus="Success"
local waypointHook
local pathService={}
function pathService:CreatePath(options)
    pathCalls+=1
    assert(options.AgentCanJump==true)
    local path={Status=pathStatus}
    function path:ComputeAsync(start,finish)
        self.Start,self.Finish=start,finish
        if computeHook then computeHook(self) end
    end
    function path:GetWaypoints()
        if waypointHook then return waypointHook(self) end
        return {{Position=self.Start,Action="Walk"},{Position=self.Finish,Action="Walk"}}
    end
    return path
end
local game={GetService=function(_,name)
    assert(name=="PathfindingService","unexpected service")
    return pathService
end}
local function contains(value,part)
    assert(string.find(tostring(value),part,1,true),"missing '"..part.."' in "..tostring(value))
end
'''


class NavigationTests(unittest.TestCase):
    def run_case(self, case):
        with tempfile.TemporaryDirectory(prefix="psx-navigation-") as temporary:
            root = Path(temporary)
            sources = root / "src"
            sources.mkdir()
            shutil.copyfile(ROOT / "src/client/Config.luau", sources / "Config.luau")
            production = ROOT / "src/client/MachineNavigation.luau"
            (sources / "MachineNavigation.luau").write_text(production.read_text() if production.exists() else 'return {new=function() return {} end}\n')
            (sources / "init.client.luau").write_text(
                'local Navigation=require(script.MachineNavigation)\n'
                'local navigation=Navigation.new(player,function(message) table.insert(progress,message) end)\n'
                'assert(type(navigation.Approach)=="function","machine navigation missing")\n'
                + case + '\nprint("NAVIGATION_TEST_OK")\n')
            output = root / "navigation.lua"
            output.write_text(FIXTURE + builder.build_bundle(sources))
            result = subprocess.run([str(ROOT / ".tools/bin/luau"), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("NAVIGATION_TEST_OK", result.stdout)

    def test_constructor_and_already_near_machine_do_not_start_walking(self):
        self.run_case('''
assert(#moves==0 and pathCalls==0)
root.Position=Vector3.new(35,0,0)
assert(navigation:Approach("Gold"))
assert(#moves==0 and pathCalls==0)
''')

    def test_walks_to_the_correct_loaded_machine_and_verifies_arrival(self):
        for variant, expected in [("Gold", 40), ("Rainbow", 80)]:
            with self.subTest(variant=variant):
                self.run_case(f'''
assert(navigation:Approach("{variant}"))
assert(pathCalls==1 and #moves>=1)
assert(math.abs(root.Position.X-{expected})<=8)
assert(#progress>0)
''')

    def test_unknown_missing_or_wrong_class_pad_does_not_move(self):
        for change, variant in [('interactive.Children={}', 'Gold'), ('gold.Children={}', 'Gold'), ('goldPad.ClassName="Folder"', 'Gold'), ('gold.ClassName="Part"', 'Gold'), ('', 'DarkMatter')]:
            with self.subTest(change=change):
                self.run_case(change + f'''
assert(not pcall(navigation.Approach,navigation,"{variant}"))
assert(pathCalls==0 and #moves==0)
''')

    def test_canceled_before_pathfinding_sends_no_move(self):
        self.run_case('''
assert(navigation:Approach("Gold",function() return false end)==false)
assert(pathCalls==0 and #moves==0)
''')

    def test_cancel_during_native_path_compute_never_starts_a_waypoint(self):
        self.run_case('''
local active=true
computeHook=function() active=false end
assert(navigation:Approach("Gold",function() return active end)==false)
assert(pathCalls==1 and #moves==0)
''')

    def test_cancel_while_walking_halts_once_without_followup_waypoints(self):
        self.run_case('''
autoMove=false
local active=true
waitHook=function() active=false end
assert(navigation:Approach("Gold",function() return active end)==false)
assert(#moves==2,"canceled navigation issued a follow-up waypoint or did not halt")
assert(moves[2]==root.Position,"last command did not halt at the current position")
''')

    def test_stop_invalidates_the_current_walk_and_halts(self):
        self.run_case('''
autoMove=false
waitHook=function() navigation:Stop() end
assert(navigation:Approach("Gold")==false)
assert(#moves==2 and moves[2]==root.Position)
navigation:Stop()
assert(#moves==2,"repeated stop issued extra movement")
''')

    def test_blocked_or_failed_path_does_not_claim_arrival(self):
        for change in ['pathStatus="NoPath"', 'computeHook=function() error("path compute failed") end', 'waypointHook=function() return {} end']:
            with self.subTest(change=change):
                self.run_case(change + '''
assert(not pcall(navigation.Approach,navigation,"Gold"))
assert(#moves==0)
''')

    def test_path_success_alone_does_not_bypass_actual_distance_and_timeout(self):
        self.run_case('''
autoMove=false
local ok,message=pcall(navigation.Approach,navigation,"Gold")
assert(not ok)
contains(message,"timed out")
assert(root.Position.X==0 and #moves==2)
''')

    def test_machine_move_or_unload_during_walk_stops_before_any_other_waypoint(self):
        for change in ['goldPad.Position=Vector3.new(90,0,0)', 'goldPad.Parent=nil', 'map.Parent=nil']:
            with self.subTest(change=change):
                self.run_case('''
autoMove=false
waitHook=function() ''' + change + ''' end
local ok,message=pcall(navigation.Approach,navigation,"Gold")
assert(not ok)
assert(#moves==2 and moves[2]==root.Position)
''')

    def test_respawn_or_dead_character_cancels_followup_walking(self):
        for change, expected in [('player.Character=instance("Replacement","Model",workspace)', 1), ('humanoid.Health=0', 2)]:
            with self.subTest(change=change):
                self.run_case('''
autoMove=false
waitHook=function() ''' + change + ''' end
assert(navigation:Approach("Gold")==false)
assert(#moves==''' + str(expected) + ''')
if #moves==2 then assert(moves[2]==root.Position) end
''')

    def test_jump_waypoints_are_executed_before_arrival(self):
        self.run_case('''
waypointHook=function(path)
    return {{Position=Vector3.new(20,0,0),Action="Jump"},{Position=path.Finish,Action="Walk"}}
end
assert(navigation:Approach("Gold"))
assert(humanoid.Jump==true)
''')

    def test_nearby_jump_waypoint_is_not_skipped_as_already_reached(self):
        self.run_case('''
waypointHook=function(path)
    return {{Position=Vector3.new(2,0,0),Action="Jump"},{Position=path.Finish,Action="Walk"}}
end
assert(navigation:Approach("Gold"))
assert(humanoid.Jump==true,"nearby jump action was skipped before the obstacle")
''')

    def test_native_cancellation_owner_releases_after_thread_is_closed(self):
        self.run_case('''
autoMove=false
waitHook=function() coroutine.yield("walking") end
local worker=coroutine.create(function() navigation:Approach("Gold") end)
assert(coroutine.resume(worker))
assert(not pcall(navigation.Approach,navigation,"Rainbow"),"overlap was permitted")
assert(coroutine.close(worker))
autoMove=true
waitHook=nil
assert(navigation:Approach("Rainbow"),"closed navigation owner remained permanently busy")
''')

    def test_pad_removed_during_path_compute_cannot_start_walking(self):
        self.run_case('''
computeHook=function() goldPad.Parent=nil end
assert(not pcall(navigation.Approach,navigation,"Gold"))
assert(#moves==0)
''')

    def test_replaced_root_or_humanoid_inside_same_character_cancels_arrival(self):
        for change in [
            'root.Name="OldRoot"; local replacement=instance("HumanoidRootPart","Part",character); replacement.Position=Vector3.new(1000,0,0)',
            'local replacement=instance("ReplacementHumanoid","Humanoid",character); replacement.Health=100; table.insert(character.Children,1,replacement)',
        ]:
            with self.subTest(change=change):
                self.run_case('''
computeHook=function() ''' + change + ''' end
assert(navigation:Approach("Gold")==false,"replaced rig component allowed false arrival")
assert(#moves==0)
''')

    def test_halt_after_root_replacement_uses_current_root_position(self):
        self.run_case('''
autoMove=false
local replacement
waitHook=function()
    root.Name="OldRoot"
    replacement=instance("HumanoidRootPart","Part",character)
    replacement.Position=Vector3.new(25,0,0)
end
assert(navigation:Approach("Gold")==false)
assert(#moves==2 and moves[2]==replacement.Position,"halt drove current rig toward a stale root position")
''')

    def test_halt_never_commands_a_replaced_humanoid(self):
        self.run_case('''
autoMove=false
waitHook=function()
    local replacement=instance("ReplacementHumanoid","Humanoid",character)
    replacement.Health=100
    function replacement:MoveTo() error("new humanoid received stale halt") end
    table.insert(character.Children,1,replacement)
end
assert(navigation:Approach("Gold")==false)
assert(#moves==1,"replaced humanoid still received a movement command")
''')

    def test_respawn_halt_cannot_command_either_old_or_replacement_rig(self):
        self.run_case('''
autoMove=false
local newMoves=0
waitHook=function()
    local replacement=instance("Replacement","Model",workspace)
    local newRoot=instance("HumanoidRootPart","Part",replacement)
    newRoot.Position=Vector3.new(500,0,0)
    local newHumanoid=instance("Humanoid","Humanoid",replacement)
    newHumanoid.Health=100
    function newHumanoid:MoveTo() newMoves+=1 end
    player.Character=replacement
end
assert(navigation:Approach("Gold")==false)
assert(#moves==1 and newMoves==0,"stale cleanup commanded an old or replacement rig")
''')

    def test_approaches_only_the_selected_loaded_egg_center(self):
        self.run_case('''
assert(type(navigation.ApproachEgg)=="function","egg navigation missing")
assert(navigation:ApproachEgg(egg))
assert(pathCalls==1 and math.abs(root.Position.X-120)<=8)
''')

    def test_already_near_egg_sends_no_path_or_move(self):
        self.run_case('''
assert(type(navigation.ApproachEgg)=="function","egg navigation missing")
root.Position=Vector3.new(115,0,0)
assert(navigation:ApproachEgg(egg))
assert(pathCalls==0 and #moves==0)
''')

    def test_missing_invalid_or_unloaded_egg_center_is_rejected(self):
        for change in ['egg.Children={}', 'eggCenter.ClassName="Folder"', 'eggCenter.Position=Vector3.new(0/0,0,0)', 'egg.Parent=nil', 'eggs.Parent=nil', 'egg.ClassName="Folder"']:
            with self.subTest(change=change):
                self.run_case('''
assert(type(navigation.ApproachEgg)=="function","egg navigation missing")
''' + change + '''
assert(not pcall(navigation.ApproachEgg,navigation,egg))
assert(pathCalls==0 and #moves==0)
''')

    def test_moved_or_unloaded_selected_egg_stops_without_another_waypoint(self):
        for change in ['eggCenter.Position=Vector3.new(200,0,0)', 'eggCenter.Parent=nil', 'egg.Parent=nil', 'eggs.Parent=nil']:
            with self.subTest(change=change):
                self.run_case('''
assert(type(navigation.ApproachEgg)=="function","egg navigation missing")
autoMove=false
waitHook=function() ''' + change + ''' end
assert(not pcall(navigation.ApproachEgg,navigation,egg))
assert(#moves==2 and moves[2]==root.Position)
''')

    def test_canceled_egg_compute_and_walk_never_continue(self):
        for cancel in ['compute', 'walk']:
            with self.subTest(cancel=cancel):
                self.run_case('''
assert(type(navigation.ApproachEgg)=="function","egg navigation missing")
local active=true
''' + ('computeHook=function() active=false end\n' if cancel == 'compute' else 'autoMove=false; waitHook=function() active=false end\n') + '''
assert(navigation:ApproachEgg(egg,function() return active end)==false)
assert(#moves==''' + ('0' if cancel == 'compute' else '2') + ''')
''')

    def test_egg_and_machine_walks_share_the_same_owner_slot(self):
        self.run_case('''
assert(type(navigation.ApproachEgg)=="function","egg navigation missing")
autoMove=false
waitHook=function() coroutine.yield("walking") end
local worker=coroutine.create(function() navigation:ApproachEgg(egg) end)
assert(coroutine.resume(worker))
assert(not pcall(navigation.Approach,navigation,"Gold"),"machine walk overlapped egg walk")
navigation:Stop()
assert(coroutine.resume(worker))
autoMove=true
waitHook=nil
assert(navigation:Approach("Gold"),"released egg owner blocked machine walk")
''')
