--!nocheck
-- Walk to loaded interaction pads; no teleporting, remotes or range spoofing.
local Config = require(script.Parent.Config)
local Navigation = {}
Navigation.__index = Navigation

local ARRIVAL_DISTANCE = 8
local WAYPOINT_DISTANCE = 4

local function finite(value)
    return type(value) == "number" and value == value and math.abs(value) < math.huge
end

local function position(value)
    return typeof(value) == "Vector3" and finite(value.X) and finite(value.Y) and finite(value.Z)
end

local function child(parent, name)
    return parent and parent:FindFirstChild(name)
end

function Navigation.new(player, onProgress)
    return setmetatable({ Player = player, OnProgress = onProgress, _generation = 0 }, Navigation)
end

function Navigation:_progress(message)
    self.Stage = message
    if type(self.OnProgress) == "function" then pcall(self.OnProgress, message) end
end

function Navigation:_halt(state)
    if not state or not state.moving then return end
    state.moving = false
    local character = self.Player.Character
    if character ~= state.character or not character.Parent or state.humanoid.Parent ~= character
        or character:FindFirstChildOfClass("Humanoid") ~= state.humanoid then return end
    -- A rig may replace its root without replacing the character/humanoid.
    -- Halt at the current root, never drive that rig toward a captured old part.
    local root = child(character, "HumanoidRootPart")
    if not root or not root:IsA("BasePart") or root.Parent ~= character or not position(root.Position) then return end
    pcall(function() state.humanoid:MoveTo(root.Position) end)
end

function Navigation:Stop()
    self._generation += 1
    local state = self._state
    self._state = nil
    self:_halt(state)
end

function Navigation:Approach(variant, active)
    if active and not active() then return false end
    local names = { Gold = "Gold Machine", Rainbow = "Rainbow Machine" }
    local name = names[variant]
    if not name then error("Choose Gold or Rainbow machine navigation.", 0) end
    local map = workspace:FindFirstChild("__MAP")
    local interactive = child(map, "Interactive")
    local machine = child(interactive, name)
    local pad = child(machine, "Pad")
    if not machine or not machine:IsA("Model") or not pad or not pad:IsA("BasePart") or not position(pad.Position) then
        error(name .. " has no loaded __MAP.Interactive model with a Pad part. Enter its world and load the machine normally.", 0)
    end
    local target = pad.Position
    return self:_walk(name, target, function()
        return workspace:FindFirstChild("__MAP") == map and map.Parent ~= nil
            and child(map, "Interactive") == interactive and interactive.Parent == map
            and child(interactive, name) == machine and machine.Parent == interactive
            and child(machine, "Pad") == pad and pad.Parent == machine and position(pad.Position)
            and (pad.Position - target).Magnitude <= 0.1
    end, active)
end

function Navigation:ApproachEgg(model, active)
    if active and not active() then return false end
    if typeof(model) ~= "Instance" or not model:IsA("Model") or not model:IsDescendantOf(workspace) then
        error("The selected egg is not a loaded workspace Model. Enter its world and load it normally.", 0)
    end
    local center = child(model, "Center")
    if not center or not center:IsA("BasePart") or not position(center.Position) then
        error("The selected egg has no loaded Center part with a readable position.", 0)
    end
    local target = center.Position
    local name = "egg " .. model.Name
    return self:_walk(name, target, function()
        return model:IsDescendantOf(workspace) and child(model, "Center") == center
            and center.Parent == model and position(center.Position)
            and (center.Position - target).Magnitude <= 0.1
    end, active)
end

function Navigation:_walk(name, target, stillLoaded, active)
    if active and not active() then return false end
    if self._owner and coroutine.status(self._owner) == "dead" then
        self:_halt(self._state)
        self._state, self._owner = nil, nil
    end
    if self._owner then error("A previous machine walk is still returning; no overlapping walk started.", 0) end
    local character = self.Player.Character
    local root = child(character, "HumanoidRootPart")
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    if not character or not character.Parent or not root or not root:IsA("BasePart") or not position(root.Position)
        or not humanoid or not finite(humanoid.Health) or humanoid.Health <= 0 then
        error("A living character with HumanoidRootPart is required to walk to an interaction.", 0)
    end
    local generation = self._generation
    local owner = coroutine.running()
    local state = { character = character, root = root, humanoid = humanoid, moving = false }
    local timeout = if finite(Config.TravelTimeout) and Config.TravelTimeout > 0 then Config.TravelTimeout else 60
    local deadline = os.clock() + timeout
    self._state, self._owner = state, owner

    local function current()
        if self._generation ~= generation or self._state ~= state or self.Player.Character ~= character
            or not character.Parent or root.Parent ~= character or humanoid.Parent ~= character
            or child(character, "HumanoidRootPart") ~= root or character:FindFirstChildOfClass("Humanoid") ~= humanoid
            or not finite(humanoid.Health) or humanoid.Health <= 0 or (active and not active()) then return false end
        if not stillLoaded() then
            error(name .. " moved or unloaded while walking; no interaction request should be sent.", 0)
        end
        if not position(root.Position) then error("Character position became unreadable while walking.", 0) end
        if os.clock() >= deadline then error("Walking to " .. name .. " timed out before verified arrival.", 0) end
        return true
    end

    local ok, result = pcall(function()
        if not current() then return false end
        if (root.Position - target).Magnitude <= ARRIVAL_DISTANCE then return true end
        self:_progress("Finding a walking path to " .. name .. "...")
        if not current() then return false end
        local service = game:GetService("PathfindingService")
        local path = service:CreatePath({ AgentCanJump = true, WaypointSpacing = 4 })
        if not current() then return false end
        path:ComputeAsync(root.Position, target)
        if not current() then return false end
        if path.Status ~= Enum.PathStatus.Success then
            error("No walkable path to " .. name .. ". Move nearer or enter the correct unlocked area, then retry.", 0)
        end
        local waypoints = path:GetWaypoints()
        if not current() then return false end
        if type(waypoints) ~= "table" or #waypoints == 0 then error("Pathfinding returned no walking waypoints.", 0) end
        for _, waypoint in ipairs(waypoints) do
            if not current() then return false end
            if (root.Position - target).Magnitude <= ARRIVAL_DISTANCE then break end
            if not position(waypoint.Position) then error("Pathfinding returned an unreadable waypoint.", 0) end
            -- A nearby jump can still be required to clear the next obstacle.
            if (root.Position - waypoint.Position).Magnitude <= WAYPOINT_DISTANCE
                and waypoint.Action ~= Enum.PathWaypointAction.Jump then continue end
            self:_progress("Walking to " .. name .. " (" .. tostring(math.ceil((root.Position - target).Magnitude)) .. " studs)...")
            if not current() then return false end
            if waypoint.Action == Enum.PathWaypointAction.Jump then humanoid.Jump = true end
            state.moving = true
            humanoid:MoveTo(waypoint.Position)
            while true do
                if not current() then return false end
                if (root.Position - target).Magnitude <= ARRIVAL_DISTANCE
                    or (root.Position - waypoint.Position).Magnitude <= WAYPOINT_DISTANCE then break end
                task.wait(0.1)
            end
        end
        if not current() then return false end
        if (root.Position - target).Magnitude > ARRIVAL_DISTANCE then
            error("Walking ended too far from " .. name .. "; no interaction request should be sent.", 0)
        end
        self:_progress("Arrived near " .. name .. "; checking interaction eligibility.")
        if not current() then return false end
        return (root.Position - target).Magnitude <= ARRIVAL_DISTANCE
    end)
    -- Only this state's movement may be halted; a stale walk cannot stop a newer one.
    self:_halt(state)
    if self._state == state then self._state = nil end
    if self._owner == owner then self._owner = nil end
    if not ok then error(result, 0) end
    return result
end

return Navigation
