--!nocheck
local Runtime = require(script.Runtime)

if not game:IsLoaded() then game.Loaded:Wait() end
local player = game:GetService("Players").LocalPlayer
assert(player, "Run the suite in a Roblox client, after joining the Classic Event.")
local parent = player:WaitForChild("PlayerGui", 15)
assert(parent, "PlayerGui was not available within 15 seconds.")

-- BindableEvent works in both Studio and executor environments, without getgenv.
-- A repeated run tells the prior session to restore changes before replacing it.
local markerName = "PetSim99AutomationSuiteSession"
-- Recognize older releases so renaming never leaves two suites running.
for _, name in ipairs({ markerName, "PetSimAutomationSession" }) do
    local previous = parent:FindFirstChild(name)
    if previous then
        if not previous:IsA("BindableEvent") then
            error("A conflicting session marker already exists; unload it first.")
        end
        previous:Fire()
        local deadline = os.clock() + 3
        while previous.Parent and os.clock() < deadline do task.wait() end
        assert(not previous.Parent, "Previous suite did not unload; remove its session before retrying.")
    end
end
local marker = Instance.new("BindableEvent")
marker.Name = markerName
marker.Parent = parent
local ok, runtime = pcall(Runtime.new, player, parent)
if not ok then
    marker:Destroy()
    error(runtime)
end
local connection
connection = marker.Event:Connect(function()
    runtime:Destroy()
end)
runtime.OnDestroy = function()
    connection:Disconnect()
    marker:Destroy()
end
