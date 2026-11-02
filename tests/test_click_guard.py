"""Execute the input permission guard at explicit focus/cursor/GUI boundaries."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("click_guard_builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

FIXTURE = r'''
local nativeTypeof = typeof
local function typeof(value)
    if type(value) == "table" and value.ClassName then return "Instance" end
    return nativeTypeof(value)
end
local guiClasses = {Frame=true,ScrollingFrame=true,CanvasGroup=true,TextButton=true,
    ImageButton=true,TextBox=true,TextLabel=true,ImageLabel=true}
local function object(class, parent)
    local value = {ClassName=class,Parent=parent,Visible=true,Active=false,
        BackgroundTransparency=1,TextTransparency=1,TextStrokeTransparency=1,
        ImageTransparency=1,GroupTransparency=0,Enabled=true,Text="Visible label",Image="rbxassetid://1"}
    function value:IsA(kind)
        return self.ClassName==kind or (kind=="GuiObject" and guiClasses[self.ClassName]==true)
            or (kind=="GuiButton" and (self.ClassName=="TextButton" or self.ClassName=="ImageButton"))
            or (kind=="LayerCollector" and self.ClassName=="ScreenGui")
    end
    return value
end
local gui = object("PlayerGui")
local screen = object("ScreenGui",gui)
local player = {}
function player:FindFirstChild(name) if name=="PlayerGui" then return gui end end
local hits, focused, cursor = {}, nil, {X=200,Y=250}
local queryCalls, focusCalls, queryX, queryY = 0,0,nil,nil
function gui:GetGuiObjectsAtPosition(x,y)
    queryCalls+=1; queryX=x; queryY=y
    return hits
end
local input = {}
function input:GetFocusedTextBox() focusCalls+=1;return focused end
function input:GetMouseLocation() return cursor end
local service = {MenuIsOpen=false}
local active = function() return true end
local function rejected(check, reason)
    assert(check==false,"guard should fail closed: "..tostring(reason))
    assert(type(reason)=="string" and #reason>0,"blocked input needs an actionable reason")
end
'''


class ClickGuardTests(unittest.TestCase):
    def run_case(self, case):
        with tempfile.TemporaryDirectory(prefix="psx-click-guard-") as temporary:
            root = Path(temporary)
            sources = root / "src"
            sources.mkdir()
            production = ROOT / "src/client/ClickGuard.luau"
            (sources / "ClickGuard.luau").write_text(
                production.read_text() if production.exists()
                else 'return {Check=function() return nil,"click guard missing" end}\n')
            (sources / "init.client.luau").write_text(
                'local Guard=require(script.ClickGuard)\n' + case + '\nprint("CLICK_GUARD_OK")\n')
            output = root / "guard.lua"
            output.write_text(FIXTURE + builder.build_bundle(sources))
            result = subprocess.run([str(ROOT / ".tools/bin/luau"), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("CLICK_GUARD_OK", result.stdout)

    def test_clear_view_uses_current_mouse_coordinates_and_positive_focus(self):
        self.run_case('''
local permitted,reason=Guard.Check(player,input,service,active)
assert(permitted==true and reason==nil,"clear view was not permitted")
assert(focusCalls==1 and queryCalls==1 and queryX==200 and queryY==250)
''')

    def test_missing_false_or_failing_focus_stops_before_cursor_gui_queries(self):
        for value in ['nil', 'function() return false end', 'function() error("focus unavailable") end', 'function() return "yes" end']:
            with self.subTest(value=value):
                self.run_case('active=' + value + '''
local permitted,reason=Guard.Check(player,input,service,active)
rejected(permitted,reason)
assert(queryCalls==0,"unfocused input queried GUI and could proceed")
''')

    def test_text_focus_and_system_menu_block_input(self):
        for change in ['focused=object("TextBox",screen)', 'service.MenuIsOpen=true']:
            with self.subTest(change=change):
                self.run_case(change + '''
local permitted,reason=Guard.Check(player,input,service,active)
rejected(permitted,reason)
assert(queryCalls==0)
''')

    def test_visible_interactive_or_nontransparent_gui_blocks_clicks(self):
        for class_name, properties in [
            ('TextButton',''), ('ImageButton',''), ('TextBox',''),
            ('Frame','hit.Active=true'), ('Frame','hit.BackgroundTransparency=0.4'),
            ('ImageLabel','hit.ImageTransparency=0'), ('TextLabel','hit.TextTransparency=0'),
            ('TextLabel','hit.TextStrokeTransparency=0'),
        ]:
            with self.subTest(class_name=class_name, properties=properties):
                self.run_case('local hit=object("' + class_name + '",screen)\n' + properties + '''
hits={hit}
local permitted,reason=Guard.Check(player,input,service,active)
rejected(permitted,reason)
''')

    def test_hidden_or_disabled_ancestry_cannot_intercept_click(self):
        for change in ['screen.Enabled=false', 'parent.Visible=false']:
            with self.subTest(change=change):
                self.run_case('''
local parent=object("Frame",screen)
local hit=object("TextButton",parent)
hits={hit}
''' + change + '''
assert(Guard.Check(player,input,service,active)==true,"hidden ancestor blocked a clear view")
''')

    def test_transparent_render_group_still_blocks_interactive_descendants(self):
        for kind in ["TextButton", "TextBox", "Frame"]:
            with self.subTest(kind=kind):
                self.run_case('''
local group=object("CanvasGroup",screen)
group.GroupTransparency=1
local hit=object("''' + kind + '''",group)
hit.Active=true
hits={hit}
rejected(Guard.Check(player,input,service,active))
''')

    def test_transparent_passive_group_does_not_hide_a_visible_outer_panel(self):
        self.run_case('''
local outer=object("Frame",screen)
local group=object("CanvasGroup",outer)
group.GroupTransparency=1
local hit=object("Frame",group)
hit.BackgroundTransparency=0
hits={hit}
assert(Guard.Check(player,input,service,active)==true,"render-hidden passive content blocked input")
outer.BackgroundTransparency=0
rejected(Guard.Check(player,input,service,active))
''')

    def test_fully_transparent_passive_wrappers_allow_world_click(self):
        self.run_case('''
local parent=object("Frame",screen)
hits={object("Frame",parent),object("TextLabel",parent),object("ImageLabel",parent),object("CanvasGroup",parent)}
assert(Guard.Check(player,input,service,active)==true)
local emptyText=object("TextLabel",parent)
emptyText.Text="";emptyText.TextTransparency=0;emptyText.TextStrokeTransparency=0
local emptyImage=object("ImageLabel",parent)
emptyImage.Image="";emptyImage.ImageTransparency=0
hits={emptyText,emptyImage}
assert(Guard.Check(player,input,service,active)==true,"empty passive image/text wrappers blocked input")
''')

    def test_opaque_parent_blocks_even_if_hit_list_only_contains_transparent_child(self):
        self.run_case('''
local parent=object("Frame",screen)
parent.BackgroundTransparency=0
hits={object("TextLabel",parent)}
rejected(Guard.Check(player,input,service,active))
''')

    def test_missing_native_queries_and_malformed_results_fail_closed(self):
        for change in [
            'input.GetFocusedTextBox=nil', 'input.GetMouseLocation=nil', 'gui.GetGuiObjectsAtPosition=nil',
            'player.FindFirstChild=nil', 'service.MenuIsOpen=nil', 'cursor={X=0/0,Y=10}',
            'cursor={X=math.huge,Y=10}', 'cursor={X=20,Y="10"}', 'hits="invalid"',
            'hits={false}', 'hits={[3]=object("Frame",screen)}',
            'local hit=object("Frame",screen);hit.Visible="yes";hits={hit}',
            'local hit=object("Frame",screen);hit.Active="yes";hits={hit}',
            'local hit=object("Frame",screen);hit.BackgroundTransparency=0/0;hits={hit}',
            'local hit=object("Frame",screen);hit.BackgroundTransparency=-1;hits={hit}',
        ]:
            with self.subTest(change=change):
                self.run_case(change + '''
local permitted,reason=Guard.Check(player,input,service,active)
rejected(permitted,reason)
''')

    def test_query_exceptions_fail_closed_without_dumping_details(self):
        self.run_case('''
function gui:GetGuiObjectsAtPosition() error("private runtime detail") end
local permitted,reason=Guard.Check(player,input,service,active)
rejected(permitted,reason)
assert(not string.find(reason,"private runtime detail",1,true))
''')

    def test_every_call_rechecks_live_focus_menu_cursor_and_gui_state(self):
        self.run_case('''
assert(Guard.Check(player,input,service,active)==true)
hits={object("TextButton",screen)}
rejected(Guard.Check(player,input,service,active))
hits={}
service.MenuIsOpen=true
rejected(Guard.Check(player,input,service,active))
service.MenuIsOpen=false
cursor={X=20,Y=30}
assert(Guard.Check(player,input,service,active)==true)
assert(queryX==20 and queryY==30)
''')
