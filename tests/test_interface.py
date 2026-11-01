"""Run the actual UI module against explicit input/viewport event fixtures."""
import importlib.util
from pathlib import Path
import tempfile
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ui_test_builder", ROOT / "scripts/build.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)

FIXTURE = r'''

local records, allConnections = {}, {}
local function signal()
    local listeners = {}
    return {
        Connect = function(self, callback)
            local connection = { Connected = true }
            function connection:Disconnect() self.Connected = false end
            table.insert(listeners, { callback, connection })
            table.insert(allConnections, connection)
            return connection
        end,
        Fire = function(self, ...)
            for _, entry in ipairs(listeners) do
                if entry[2].Connected then entry[1](...) end
            end
        end,
    }
end
local eventNames = { Activated=true, FocusLost=true, InputBegan=true, InputChanged=true, InputEnded=true }
local Instance = {}
function Instance.new(class)
    local item = { ClassName = class, AbsoluteSize = { X=600, Y=800 } }
    for name in pairs(eventNames) do item[name] = signal() end
    item.PropertySignals = {}
    function item:GetPropertyChangedSignal(name)
        if not self.PropertySignals[name] then self.PropertySignals[name] = signal() end
        return self.PropertySignals[name]
    end
    function item:IsFocused() return false end
    function item:Destroy() self.Destroyed = true end
    table.insert(records, item)
    return item
end
local Enum = setmetatable({}, { __index=function(self, key)
    local enum = setmetatable({}, { __index=function(_, name) return key .. '.' .. name end })
    rawset(self,key,enum)
    return enum
end })
local Color3 = { fromRGB=function(r,g,b) return {r,g,b} end }
local Vector2 = { new=function(x,y) return {X=x,Y=y} end }
local UDim = { new=function(scale,offset) return {Scale=scale,Offset=offset} end }
local UDim2 = {}
function UDim2.new(xs,xo,ys,yo) return {X=UDim.new(xs or 0,xo or 0),Y=UDim.new(ys or 0,yo or 0)} end
function UDim2.fromScale(x,y) return UDim2.new(x,0,y,0) end
function UDim2.fromOffset(x,y) return UDim2.new(0,x,0,y) end
local input = { InputBegan=signal(), InputChanged=signal(), InputEnded=signal() }
function input:GetFocusedTextBox() return nil end
local game = { GetService=function() return input end }
'''

class InterfaceTests(unittest.TestCase):
    def run_case(self, case):
        with tempfile.TemporaryDirectory(prefix="psx-interface-") as directory:
            root = Path(directory)
            sources = root / "src"
            sources.mkdir()
            (sources / "Interface.luau").write_text((ROOT / "src/client/Interface.luau").read_text())
            entry = "local Interface = require(script.Interface)\n" + case
            (sources / "init.client.luau").write_text(entry)
            output = root / "interface-test.lua"
            output.write_text(FIXTURE + "\n" + builder.build_bundle(sources))
            result = subprocess.run([str(ROOT / ".tools/bin/luau"), str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_viewport_resize_keeps_dragged_controls_reachable(self):
        self.run_case('''
local ui = Interface.mount({parent={}, name="Suite", version="test", options={}, onChange=function() return true end, onAction=function() end})
local gui, panel
for _, object in ipairs(records) do
    if object.Name == "PetSimAutomationUi" then gui = object end
    if object.Name == "Panel" then panel = object end
end
panel.Position = UDim2.fromOffset(1000, 700)
panel.AbsoluteSize = { X=520, Y=400 }
gui.AbsoluteSize = { X=600, Y=480 }
gui:GetPropertyChangedSignal("AbsoluteSize"):Fire()
local x = panel.Position.X.Scale * 600 + panel.Position.X.Offset
local y = panel.Position.Y.Scale * 480 + panel.Position.Y.Offset
assert(x >= 260 and x <= 340 and y >= 200 and y <= 280,
    "resizing left the Stop/Unload controls offscreen")
ui:Destroy()
''')

    def test_panel_size_change_reclamps_and_unload_disconnects_resize_handlers(self):
        self.run_case('''
local ui = Interface.mount({parent={}, onChange=function() return true end, onAction=function() end})
local gui, panel
for _, object in ipairs(records) do
    if object.Name == "PetSimAutomationUi" then gui = object end
    if object.Name == "Panel" then panel = object end
end
gui.AbsoluteSize = { X=600, Y=480 }
panel.Position = UDim2.fromOffset(590, 470)
panel.AbsoluteSize = { X=520, Y=400 }
panel:GetPropertyChangedSignal("AbsoluteSize"):Fire()
local x = panel.Position.X.Scale * 600 + panel.Position.X.Offset
local y = panel.Position.Y.Scale * 480 + panel.Position.Y.Offset
assert(x <= 340 and y <= 280, "expanding the panel stranded its controls")
ui:Destroy()
for _, connection in ipairs(allConnections) do assert(not connection.Connected, "unload leaked an input/resize handler") end
local oldPosition = panel.Position
gui:GetPropertyChangedSignal("AbsoluteSize"):Fire()
assert(panel.Position == oldPosition)
''')
