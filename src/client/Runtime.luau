--!nocheck
local Config = require(script.Parent.Config)
local Policy = require(script.Parent.Policy)
local Jobs = require(script.Parent.Jobs)
local Interface = require(script.Parent.Interface)
local PetSim99 = require(script.Parent.PetSim99)
local PetCare = require(script.Parent.PetCare)
local MachineNavigation = require(script.Parent.MachineNavigation)

local Lighting = game:GetService("Lighting")
local HttpService = game:GetService("HttpService")
local Runtime = {}
Runtime.__index = Runtime

function Runtime.new(player, parent)
    local self = setmetatable({
        Player = player, Alive = true, Connections = {}, Jobs = Jobs.new(),
        Options = table.clone(Config.Options), Adapter = PetSim99.new(), Care = PetCare.new(),
        Ready = false, Failures = {}, NextAt = {},
        State = { Status = "Idle — run the compatibility check manually", Target = "None", EquippedPets = 0,
            Farmed = 0, CollectedOrbs = 0, CollectedLootbags = 0, LastError = "",
            CareStatus = "Pet tools idle — click Load pet tools", HatchRequests = 0, GoldRequests = 0, RainbowRequests = 0 },
    }, Runtime)
    self.Navigator = MachineNavigation.new(player, function(message)
        if not self.Alive then return end
        self.State.CareStatus = message
        self:Publish()
    end)
    self.Ui = Interface.mount({
        parent = parent, name = Config.Name, version = Config.Version, options = self.Options,
        onChange = function(key, value) return self:SetOption(key, value) end,
        onAction = function(action) return self:Action(action) end,
    })
    table.insert(self.Connections, player.CharacterAdded:Connect(function(character)
        for _, key in ipairs({ "AutoFarm", "AutoCollectOrbs", "AutoCollectLootbags" }) do self.Jobs:cancel(key) end
        if self.Options.HeavenChestAssist then self:StopHeavenChest() end
        if self.Options.HeavenIslandSweep then self:StopHeavenSweep() end
        self.Jobs:cancel("care")
        self.Navigator:Stop()
        self:StopNavigation()
        self.LastAssignment = nil
        self.NextAt = {}
        self:RestoreMovement()
        self.Jobs:cancel("movement")
        self.Jobs:start("movement", 10, function()
            return character:WaitForChild("Humanoid", 8)
        end, function(ok, humanoid)
            if ok and humanoid and self.Options.MovementEnabled then self:ApplyMovement(humanoid) end
        end)
    end))
    table.insert(self.Connections, player.Idled:Connect(function()
        if not self.Options.AntiIdle then return end
        local ok, message = pcall(function()
            local user = game:GetService("VirtualUser")
            user:CaptureController()
            user:ClickButton2(Vector2.new(0, 0))
        end)
        if not ok then
            self.Options.AntiIdle = false
            self.AntiIdleUnavailable = true
            self.State.LastError = "Idle input unsupported: " .. tostring(message)
            self:Publish()
        end
    end))
    -- B toggles only the local Heaven Island input farm. Respect UI text input.
    local inputOk, input = pcall(function() return game:GetService("UserInputService") end)
    if inputOk and input and input.InputBegan then
        table.insert(self.Connections, input.InputBegan:Connect(function(key, processed)
            if processed or not self.Alive or not key or not Enum or not Enum.KeyCode
                or key.KeyCode ~= Enum.KeyCode.B then return end
            local focusOk, focused = pcall(input.GetFocusedTextBox, input)
            if focusOk and focused then return end
            if self.Options.HeavenIslandSweep then
                self:StopHeavenSweep()
            else
                local started, reason = self:StartHeavenSweep()
                if not started then
                    self.State.LastError = "B AutoFarm toggle: " .. tostring(reason)
                    self:Publish()
                end
            end
        end))
    end
    table.insert(self.Connections, game:GetService("TeleportService").TeleportInitFailed:Connect(function(who, _, message)
        if who == player and self.Alive then
            self.State.LastError = "Rejoin failed: " .. tostring(message)
            self:Publish()
        end
    end))
    self:Publish()
    -- Initial local scan runs automatically on load, with no game module or remote calls.
    local scanOk, scanMessage = pcall(function() self:ScanHeavenTargets() end)
    if not scanOk then
        self.State.HeavenScanStatus = "Initial local scan unavailable: " .. tostring(scanMessage)
        self:Publish()
    end
    self.Pulse = task.spawn(function()
        while self.Alive do
            local ok, message = pcall(function()
                self.Jobs:tick()
                self:Step()
            end)
            if not ok then
                self:StopAll()
                self.State.LastError = "Scheduler stopped: " .. tostring(message)
                self:Publish()
            end
            task.wait(0.25)
        end
    end)
    return self
end

-- Heaven Island chest input helper. Does not use Save.Get, game remotes or
-- the legacy Get Coins protocol. It clicks once per captured BasePart instance
-- and waits until that part disappears before clicking a matching replacement.
-- The actual game-side response is not confirmed by a synthetic click.
function Runtime:ArmHeavenChest()
    if not self.Alive then return false, "Suite unloaded." end
    if type(mouse1click) ~= "function" then
        return false, "This executor has no mouse1click() support."
    end
    self.Options.HeavenChestAssist = true
    self.ChestArmAt = os.clock() + 3
    self.ChestClickedPart, self.ChestAnchorPosition = nil, nil
    self.ChestAnchorName, self.ChestAnchorParent = nil, nil
    self.State.ChestStatus = "Move your cursor over the Heaven chest: capturing in 3 seconds."
    self.State.LastError = ""
    self:Publish()
    return true
end

function Runtime:StopHeavenChest()
    self.Options.HeavenChestAssist = false
    self.ChestArmAt, self.ChestClickedPart, self.ChestAnchorPosition = nil, nil, nil
    self.ChestAnchorName, self.ChestAnchorParent = nil, nil
    self.State.ChestStatus = "Stopped"
    self:Publish()
    return true
end

function Runtime:StepHeavenChest()
    if not self.Options.HeavenChestAssist then return end
    local character = self.Player.Character
    if not character or not character.Parent then return end
    if type(mouse1click) ~= "function" then
        self.State.LastError = "Heaven chest input unsupported: mouse1click() is missing."
        self:StopHeavenChest()
        return
    end
    local mouse = self.Player:GetMouse()
    local target = mouse and mouse.Target
    local function usable(part)
        return part and part:IsA("BasePart") and part:IsDescendantOf(workspace)
            and not part:IsDescendantOf(character)
    end
    if self.ChestArmAt then
        if os.clock() < self.ChestArmAt then return end
        self.ChestArmAt = nil
        if not usable(target) then
            self.State.LastError = "No world BasePart under cursor. Aim at the chest when arming."
            self:StopHeavenChest()
            return
        end
        self.ChestAnchorName = target.Name
        self.ChestAnchorParent = target.Parent and target.Parent.Name or ""
        self.ChestAnchorPosition = target.Position
        self.State.ChestStatus = "Captured " .. target.Name .. "; initial click pending"
    end
    if not self.ChestAnchorPosition then return end
    if self.ChestClickedPart then
        if self.ChestClickedPart:IsDescendantOf(workspace) then return end
        self.ChestClickedPart = nil
        self.State.ChestStatus = "Chest disappeared; waiting for matching respawn under cursor"
        self:Publish()
    end
    if not usable(target) or target.Name ~= self.ChestAnchorName
        or (target.Parent and target.Parent.Name or "") ~= self.ChestAnchorParent
        or (target.Position - self.ChestAnchorPosition).Magnitude > 12 then return end
    if type(isrbxactive) == "function" then
        local ok, active = pcall(isrbxactive)
        if not ok or not active then return end
    end
    local ok, result = pcall(mouse1click)
    if not ok then
        self.State.LastError = "Heaven chest click failed: " .. tostring(result)
        self:StopHeavenChest()
        return
    end
    self.ChestClickedPart = target
    self.State.ChestClicks = (self.State.ChestClicks or 0) + 1
    self.State.ChestStatus = "Clicked once; waiting for chest to disappear (rewards unverified)"
    self:Publish()
end

-- Object-targeted Heaven Island input farm.
-- Works only with visible, recognizably named/tagged individual breakables.
-- Never guesses remotes, fabricates data, fires network events or sweeps blind pixels.
local HEAVEN_CATEGORIES = {
    { "Vault", { "vault", "safe" } },
    { "Gift", { "gift", "present" } },
    { "Chest", { "chest" } },
    { "Coin", { "coin", "pile", "diamond" } },
    { "Crate", { "crate", "breakable" } },
}
local HEAVEN_FORBIDDEN = {
    "heavens gate", "heaven's gate", "grand heaven", "angel chest", "giant",
    "big chest", "boss chest", "massive", "titanic", "huge chest", "mega chest",
}
local HEAVEN_IGNORE = {
    "__debris", "__mapdebris", "exclusiveeggs", "exclusiveeggpets", "pets",
    "orbs", "lootbags", "players", "camera",
}
local function containsAny(name, terms)
    for _, term in ipairs(terms) do
        if string.find(name, term, 1, true) then return true end
    end
    return false
end
local function heavenKind(name)
    name = string.lower(tostring(name or ""))
    for _, definition in ipairs(HEAVEN_CATEGORIES) do
        if containsAny(name, definition[2]) then return definition[1] end
    end
    return nil
end
local function heavenPosition(object)
    if object:IsA("BasePart") then return object.Position end
    if object:IsA("Model") then
        local ok, pivot = pcall(object.GetPivot, object)
        if ok and pivot then return pivot.Position end
        local part = object.PrimaryPart or object:FindFirstChildWhichIsA("BasePart", true)
        return part and part.Position
    end
    return nil
end
local function heavenDistance(a, b)
    if not a or not b then return nil end
    local ok, distance = pcall(function() return (a - b).Magnitude end)
    if ok and type(distance) == "number" then return distance end
    -- Also accept numeric XYZ vectors from benign test doubles and proxy values.
    local valid = type(a.X) == "number" and type(a.Y) == "number" and type(a.Z) == "number"
        and type(b.X) == "number" and type(b.Y) == "number" and type(b.Z) == "number"
    if not valid then return nil end
    local dx, dy, dz = a.X - b.X, a.Y - b.Y, a.Z - b.Z
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end
local function heavenExcluded(object)
    local depth, node = 0, object
    while node and node ~= workspace and depth < 14 do
        local label = string.lower(tostring(node.Name or ""))
        if containsAny(label, HEAVEN_FORBIDDEN) then return true end
        -- Never target player pets, pick-ups, debris or visual effects.
        if depth > 0 and containsAny(label, HEAVEN_IGNORE) then return true end
        node, depth = node.Parent, depth + 1
    end
    return false
end
local function heavenCandidateType(object, coinsFolder)
    if object:IsA("Model") and coinsFolder and object.Parent == coinsFolder then
        return "Coin"
    end
    local kind = heavenKind(object.Name)
    if kind then return kind end
    if type(object.GetTags) == "function" then
        local ok, tags = pcall(object.GetTags, object)
        if ok and type(tags) == "table" then
            for _, tag in ipairs(tags) do
                kind = heavenKind(tag)
                if kind then return kind end
            end
        end
    end
    if type(object.GetAttribute) == "function" then
        for _, attribute in ipairs({ "BreakableType", "CoinType", "Type" }) do
            local ok, value = pcall(object.GetAttribute, object, attribute)
            if ok and type(value) == "string" then
                kind = heavenKind(value)
                if kind then return kind end
            end
        end
    end
    return nil
end

function Runtime:ScanHeavenTargets()
    if not self.Alive then return false, "Suite unloaded." end
    local character = self.Player.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    local origin = root and root.Position
    local getAll = workspace.GetDescendants
    if type(getAll) ~= "function" then
        self.HeavenTargets = {}
        self.State.HeavenScanStatus = "Workspace listing unavailable; 0 detected targets"
        self.State.HeavenTargetCount = 0
        self:Publish()
        return false, self.State.HeavenScanStatus
    end
    local ok, objects = pcall(getAll, workspace)
    if not ok or type(objects) ~= "table" then
        self.HeavenTargets = {}
        self.State.HeavenScanStatus = "Unable to read local Workspace descendants"
        self.State.HeavenTargetCount = 0
        self:Publish()
        return false, self.State.HeavenScanStatus
    end
    local things = workspace:FindFirstChild("__THINGS")
    local coins = things and things:FindFirstChild("Coins")
    local maxRadius = math.min(160, self.Options.Radius or 160)
    local counts, targets, reviewed = {}, {}, 0
    for _, object in ipairs(objects) do
        reviewed += 1
        if reviewed > 40000 then break end
        if object:IsA("Model") or object:IsA("BasePart") then
            if not heavenExcluded(object) and (not character or not object:IsDescendantOf(character)) then
                local kind = heavenCandidateType(object, coins)
                if kind then
                    -- A named model is one breakable; don't click each of its parts.
                    local parent = object.Parent
                    if not (object:IsA("BasePart") and parent and parent:IsA("Model")
                        and heavenCandidateType(parent, coins) ~= nil) then
                        local position = heavenPosition(object)
                        local distance = heavenDistance(position, origin)
                        if distance and distance <= maxRadius and distance >= 2 then
                            local sizeAllowed = true
                            if object:IsA("Model") and type(object.GetBoundingBox) == "function" then
                                local boxOk, _, size = pcall(object.GetBoundingBox, object)
                                if boxOk and size and type(size.X) == "number" then
                                    sizeAllowed = math.max(size.X, size.Y, size.Z) <= 30
                                end
                            end
                            if sizeAllowed then
                                table.insert(targets, {
                                    instance = object, name = tostring(object.Name),
                                    kind = kind, position = position, distance = distance,
                                })
                                counts[kind] = (counts[kind] or 0) + 1
                            end
                        end
                    end
                end
            end
        end
    end
    table.sort(targets, function(a, b)
        if a.distance ~= b.distance then return a.distance < b.distance end
        return a.name < b.name
    end)
    self.HeavenTargets = targets
    self.HeavenScanAt = os.clock()
    self.HeavenScanNextAt = os.clock() + 7
    self.State.HeavenTargetCount = #targets
    local summary = {}
    for _, kind in ipairs({ "Vault", "Gift", "Chest", "Coin", "Crate" }) do
        if counts[kind] then table.insert(summary, kind .. "=" .. tostring(counts[kind])) end
    end
    self.State.HeavenScanStatus = "Scan: " .. tostring(#targets)
        .. " nearby named/tagged objects (" .. (if #summary > 0 then table.concat(summary, ", ") else "none") .. ")"
        .. "; inspected " .. tostring(math.min(reviewed, 40000)) .. " descendants"
        .. (if reviewed > 40000 then " (scan capped)" else "")
    if #targets == 0 then
        self.State.HeavenSweepStatus =
            "0 identifiable small breakables. No clicks will be sent. Game objects may be unnamed or not replicated."
    end
    self:Publish()
    return true, self.State.HeavenScanStatus
end

function Runtime:StartHeavenSweep()
    if not self.Alive then return false, "Suite unloaded." end
    if type(mouse1click) ~= "function" or type(mousemoveabs) ~= "function" then
        self.State.LastError = "Targeted AutoFarm requires mouse1click() AND mousemoveabs() in this executor."
        self:Publish()
        return false, self.State.LastError
    end
    self.Options.HeavenIslandSweep = true
    self.Options.HeavenChestAssist = false
    self.ChestArmAt, self.ChestClickedPart, self.ChestAnchorPosition = nil, nil, nil
    self.HeavenSweepNextAt = 0
    self.HeavenSweepPending = nil
    -- Each object can be retried after a cooldown, even if the same instance
    -- remains in the Workspace after a click.
    self.HeavenSweepClicked = setmetatable({}, { __mode = "k" })
    self.HeavenSweepMismatches = 0
    self.State.HeavenSweepMode = "Object targeting with mouse-hit verification; B to toggle"
    self.State.Status = "Heaven Island target AutoFarm running (input-only; no Get Coins)"
    self.State.LastError = ""
    self:ScanHeavenTargets()
    self.State.HeavenSweepStatus = if #self.HeavenTargets > 0
        then "Finding visible small targets; giant chest names excluded"
        else "Waiting for identifiable local small breakables (0 found)"
    self:Publish()
    return true
end

function Runtime:StopHeavenSweep()
    self.Options.HeavenIslandSweep = false
    self.HeavenSweepNextAt, self.HeavenSweepPending = nil, nil
    self.State.HeavenSweepStatus = "Stopped (B to restart)"
    self:Publish()
    return true
end

function Runtime:StepHeavenSweep()
    if not self.Options.HeavenIslandSweep then return end
    local now = os.clock()
    if now >= (self.HeavenScanNextAt or 0) then self:ScanHeavenTargets() end
    if now < (self.HeavenSweepNextAt or 0) then return end
    if type(mouse1click) ~= "function" or type(mousemoveabs) ~= "function" then
        self.State.LastError = "Automatic target clicking unsupported by this executor."
        self:StopHeavenSweep()
        return
    end
    if type(isrbxactive) == "function" then
        local ok, focused = pcall(isrbxactive)
        if not ok or focused ~= true then
            self.HeavenSweepNextAt = now + 1
            self.State.HeavenSweepStatus = "Paused: Roblox is not focused"
            return
        end
    end
    local okService, inputService = pcall(function() return game:GetService("UserInputService") end)
    if okService and inputService and type(inputService.GetFocusedTextBox) == "function" then
        local okInput, box = pcall(inputService.GetFocusedTextBox, inputService)
        if okInput and box then self.HeavenSweepNextAt = now + 1; return end
    end
    local camera, pending = workspace.CurrentCamera, self.HeavenSweepPending
    local viewport = camera and camera.ViewportSize
    if not camera or not viewport or type(camera.WorldToViewportPoint) ~= "function"
        or type(viewport.X) ~= "number" or type(viewport.Y) ~= "number" then
        self.HeavenSweepNextAt = now + 1
        self.State.HeavenSweepStatus = "Waiting for usable camera projection"
        return
    end
    if pending then
        if now < pending.clickAt then return end
        self.HeavenSweepPending = nil
        local object = pending.instance
        if not object:IsDescendantOf(workspace) then return end
        local readyAt = self.HeavenSweepClicked[object] or 0
        if now < readyAt then return end
        -- Validate projected aim AFTER moving the cursor, not just the object's old coordinates.
        -- This catches viewport / executor coordinate mismatches and UI overlays.
        local mouseOk, mouse = pcall(function() return self.Player:GetMouse() end)
        local hit = if mouseOk and mouse then mouse.Target else nil
        local matchesTarget = hit ~= nil
            and (hit == object or (object:IsA("Model") and hit:IsDescendantOf(object)))
        if not matchesTarget then
            self.HeavenSweepMismatches = (self.HeavenSweepMismatches or 0) + 1
            self.HeavenSweepClicked[object] = now + 1
            self.HeavenSweepNextAt = now + 0.35
            self.State.HeavenSweepStatus = "Skipped off-target cursor for " .. pending.kind
                .. " (" .. tostring(self.HeavenSweepMismatches) .. " mismatches); no click sent"
            -- Keep running; scan again when local models change.
            self:Publish()
            return
        end
        local clicked, message = pcall(mouse1click)
        if not clicked then
            self.State.LastError = "Targeted click failed: " .. tostring(message)
            self:StopHeavenSweep()
            return
        end
        self.HeavenSweepClicked[object] = now + math.max(3, (self.Options.FarmInterval or 0.75) * 3)
        self.State.HeavenSweepClicks = (self.State.HeavenSweepClicks or 0) + 1
        self.State.HeavenSweepStatus = "Clicked verified " .. pending.kind .. ": " .. pending.name
            .. " (#" .. tostring(self.State.HeavenSweepClicks) .. "; rewards unverified)"
        self.HeavenSweepNextAt = now + math.clamp(self.Options.FarmInterval or 0.75, 0.4, 5)
        self:Publish()
        return
    end
    local candidates = self.HeavenTargets or {}
    if #candidates == 0 then
        self.HeavenSweepNextAt = now + 1
        self.State.HeavenSweepStatus = "No identifiable small breakables; waiting for the next scan, no random clicks"
        return
    end
    local chosen, chosenPoint
    for _, target in ipairs(candidates) do
        if now >= (self.HeavenSweepClicked[target.instance] or 0)
            and target.instance:IsDescendantOf(workspace) then
            local projected, point, visible = pcall(camera.WorldToViewportPoint, camera, target.position)
            if projected and visible and point and type(point.Z) == "number" and point.Z > 0
                and point.X >= 35 and point.X <= viewport.X * 0.63
                and point.Y >= 110 and point.Y <= viewport.Y * 0.9 then
                -- Do not click a target obstructed by another world object.
                local clear = true
                if type(workspace.Raycast) == "function" and camera.CFrame then
                    local rayOk, hit = pcall(workspace.Raycast, workspace,
                        camera.CFrame.Position, target.position - camera.CFrame.Position)
                    if rayOk and hit and hit.Instance then
                        clear = hit.Instance == target.instance
                            or hit.Instance:IsDescendantOf(target.instance)
                    end
                end
                if clear then chosen, chosenPoint = target, point; break end
            end
        end
    end
    if not chosen then
        self.HeavenSweepNextAt = now + 1
        self.State.HeavenSweepStatus = "Scanned " .. tostring(#candidates)
            .. " objects; waiting for cooldown or a visible unblocked target"
        return
    end
    local moved, message = pcall(mousemoveabs, math.floor(chosenPoint.X), math.floor(chosenPoint.Y))
    if not moved then
        self.State.LastError = "Targeted mouse movement failed: " .. tostring(message)
        self:StopHeavenSweep()
        return
    end
    self.HeavenSweepPending = {
        instance = chosen.instance, position = chosen.position, kind = chosen.kind,
        name = chosen.name, clickAt = now + 0.20,
    }
    self.HeavenSweepNextAt = now + 0.20
    self.State.HeavenSweepStatus = "Aiming at " .. chosen.kind .. ": " .. chosen.name
end

function Runtime:StopNavigation()
    local humanoid = self.Navigating
    self.Navigating = nil
    local root = self.Player.Character and self.Player.Character:FindFirstChild("HumanoidRootPart")
    if humanoid and humanoid.Parent and root then
        pcall(function() humanoid:MoveTo(root.Position) end)
    end
end

function Runtime:FeatureResult(key, ok, result)
    if ok then
        self.Failures[key] = 0
        if type(result) == "table" then
            for field, value in pairs(result) do self.State[field] = value end
        end
    else
        self.Failures[key] = (self.Failures[key] or 0) + 1
        self.State.LastError = key .. ": " .. tostring(result)
        if self.Adapter.Supported.AutoFarm == false then
            self.Ready = false
            for _, feature in ipairs({ "AutoFarm", "AutoCollectOrbs", "AutoCollectLootbags" }) do
                self.Options[feature] = false
                self.Jobs:cancel(feature)
            end
            self:StopNavigation()
            self.State.Status = "Protocol rejected — reconnect required; see Status."
            self:Publish()
            return
        end
        self.NextAt[key] = os.clock() + math.min(8, 2 ^ self.Failures[key])
        if self.Failures[key] >= Config.RetryLimit then
            self.Options[key] = false
            self.State.Status = key .. " stopped after repeated errors; see Status."
            if key == "AutoFarm" then self:StopNavigation() end
        end
    end
    self:Publish()
end

function Runtime:PrepareCare()
    for _, key in ipairs({ "AutoHatch", "AutoGold", "AutoRainbow" }) do self.Options[key] = false end
    self.Jobs:cancel("care")
    self.Navigator:Stop()
    local started = self.Jobs:start("care", Config.RequestTimeout, function(activeJob)
        return self.Care:Connect(activeJob, self.Options.ModulePathMode)
    end, function(ok, result)
        local loaded = ok and (self.Care.Supported.AutoHatch or self.Care.Supported.AutoGold or self.Care.Supported.AutoRainbow)
        self.State.CareStatus = if loaded then self.Care.Reason else "Pet tools unavailable: " .. tostring(self.Care.Reason)
        self.State.LastError = if loaded then "" else (if ok then tostring(self.Care.Reason) else tostring(result))
            .. " [Pet stage: " .. tostring(self.Care._phase or "unknown") .. "]"
        self:Publish()
    end)
    if not started then return false, "A previous pet operation is still returning; no new request sent." end
    self:Publish()
    return true
end

function Runtime:InspectSave()
    if not self.Alive then return false, "Suite unloaded." end
    local started = self.Jobs:start("care", Config.RequestTimeout, function(activeJob)
        return self.Care:InspectSave(activeJob)
    end, function(ok, inspected)
        self.State.CareStatus = if ok and inspected
            then "Save layout inspected; see Status or Copy diagnostics" else "Save inspection unavailable; see Last Error"
        if not ok then self.State.LastError = "Save inspection: " .. tostring(inspected) end
        self:Publish()
    end)
    if not started then return false, "Pet worker busy; no overlapping Save.Get read." end
    self:Publish()
    return true
end

function Runtime:StartCare(key, manual)
    if not self.Alive then return false, "Suite unloaded." end
    if not self.Care.Supported[key] then return false, self.Care.Reason end
    local character = self.Player.Character
    if not character or not character.Parent then return false, "Wait for your character to load." end
    local egg, mode, species = self.Options.EggName, self.Options.HatchMode, self.Options.ConversionSpecies
    local travel = self.Options.MachineTravelMode == "Walk" and key ~= "AutoHatch"
    local timeout = Config.RequestTimeout + (if travel then Config.TravelTimeout else 0)
    local started = self.Jobs:start("care", timeout, function(activeJob)
        local function current()
            return self.Alive and activeJob() and self.Player.Character == character and character.Parent ~= nil
                and (manual or self.Options[key])
        end
        if key == "AutoHatch" then return self.Care:Hatch(egg, mode, current) end
        local variant = if key == "AutoGold" then "Gold" else "Rainbow"
        if not self.Care:CanConvert(variant, species, current) or not current() then return 0 end
        if travel then
            self.Jobs:cancel("AutoFarm")
            self:StopNavigation()
            if not self.Navigator:Approach(variant, current) then return 0 end
        end
        if not current() then return 0 end
        return self.Care:Convert(variant, species, current)
    end, function(ok, result)
        self.State.CareStatus = self.Care.Reason
        if not ok then
            self.Navigator:Stop()
            self.Options[key] = false
            self.State.LastError = key .. ": " .. tostring(result)
            self.State.CareStatus = "Pet operation stopped — see error"
        end
        self:Publish()
    end)
    if not started then return false, "A pet operation is still returning; no overlapping request sent." end
    return true
end

function Runtime:GoToMachine(variant, openMenu)
    if not self.Alive then return false, "Suite unloaded." end
    local character = self.Player.Character
    if not character or not character.Parent then return false, "Wait for your character to load." end
    self.Jobs:cancel("AutoFarm")
    self:StopNavigation()
    local started = self.Jobs:start("care", Config.TravelTimeout, function(activeJob)
        self.MachineJourney = activeJob
        local function current()
            return self.Alive and activeJob() and self.Player.Character == character and character.Parent ~= nil
        end
        if not self.Navigator:Approach(variant, current) or not current() then return false end
        if openMenu then self.Care:OpenMenu(variant) end
        return true
    end, function(ok, result)
        if not ok then
            self.Navigator:Stop()
            self.State.LastError = "Machine travel: " .. tostring(result)
            self.State.CareStatus = "Machine travel stopped — see error"
        elseif result then
            self.State.CareStatus = "Arrived at " .. variant .. " machine"
        end
        self:Publish()
    end)
    if not started then return false, "A pet operation is still returning; no overlapping journey started." end
    return true
end

function Runtime:StepCare()
    if not self.Alive then return end
    local now = os.clock()
    local features = { "AutoRainbow", "AutoGold", "AutoHatch" }
    local cursor = self.CareCursor or 1
    for offset = 0, #features - 1 do
        local index = (cursor + offset - 1) % #features + 1
        local key = features[index]
        if self.Options[key] and not self.Jobs:busy("care") and now >= (self.NextAt[key] or 0) then
            local interval = if key == "AutoHatch" then self.Options.HatchInterval else self.Options.ConversionInterval
            self.NextAt[key] = now + interval
            local started, reason = self:StartCare(key, false)
            if not started then
                self.Options[key] = false
                self.State.LastError = reason
                self:Publish()
            end
            self.CareCursor = index % #features + 1
            return
        end
    end
end

function Runtime:Step()
    self:StepHeavenSweep()
    self:StepHeavenChest()
    self:StepCare()
    if self.Jobs:busy("care") and (self.Options.MachineTravelMode == "Walk"
        or (self.MachineJourney and self.MachineJourney())) then
        self.Jobs:cancel("AutoFarm")
        self:StopNavigation()
        self:Publish()
        return
    end
    if not self.Ready then
        local now = os.clock()
        if now >= (self.NextPublish or 0) and (self.Jobs:busy("connect") or self.Jobs:busy("care")) then
            self.NextPublish = now + 1
            self:Publish()
        end
        return
    end
    local now = os.clock()
    local character = self.Player.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    local humanoid = character and character:FindFirstChildOfClass("Humanoid")
    if not root or not humanoid or humanoid.Health <= 0 then
        for _, key in ipairs({ "AutoFarm", "AutoCollectOrbs", "AutoCollectLootbags" }) do self.Jobs:cancel(key) end
        self:StopNavigation()
        self.LastAssignment = nil
        if self.Options.AutoFarm then self.State.Status = "Waiting for a living character..." end
        self:Publish()
        return
    end
    if self.Options.AutoFarm and not self.Jobs:busy("AutoFarm") and now >= (self.NextAt.AutoFarm or 0) then
        self.NextAt.AutoFarm = now + self.Options.FarmInterval
        self.Jobs:start("AutoFarm", Config.FarmTimeout, function(activeJob)
            local snapshot = self.Adapter:Snapshot(activeJob)
            if not activeJob() or self.Player.Character ~= character or not character.Parent or not root.Parent or humanoid.Health <= 0 then
                return { Status = "Waiting for the current character..." }
            end
            if self.Options.FarmMode ~= "Nearest" and not snapshot.HealthKnown then
                error("This coin response has no reliable health data. Select Nearest priority.")
            end
            self.State.EquippedPets = #snapshot.Pets
            local target = Policy.select(snapshot.Candidates, self.Options)
            if not target then
                self:StopNavigation()
                return { Status = "No loaded targets match radius/area/name filters.", Target = "None" }
            end
            local title = target.name .. " / " .. target.area
            if #snapshot.Pets == 0 then
                self:StopNavigation()
                return { Status = "Equip pets in-game to start farming.", Target = title }
            end
            if self.Options.WalkToTarget and target.distance > 20 then
                self.Navigating = humanoid
                humanoid:MoveTo(target.position)
                return { Status = "Walking toward target...", Target = title }
            end
            self:StopNavigation()
            local sorted = {}
            for _, uid in ipairs(snapshot.Pets) do table.insert(sorted, tostring(uid)) end
            table.sort(sorted)
            local signature = table.concat(sorted, "|")
            local last = self.LastAssignment
            if last and last.Id == target.id and last.Pets == signature and now - last.Time < Config.ReassignSeconds then
                return { Status = "Recent farm requests; watching target.", Target = title }
            end
            local count = self.Adapter:Assign(target, snapshot.Pets, function()
                return activeJob() and self.Alive and self.Options.AutoFarm and self.Player.Character == character
                    and character.Parent ~= nil and root.Parent ~= nil and humanoid.Parent ~= nil and humanoid.Health > 0
            end)
            if count > 0 then
                self.LastAssignment = { Id = target.id, Pets = signature, Time = os.clock() }
            end
            return { Status = if count > 0 then "Farm requests sent; waiting for game response." else self.Adapter.Reason, Target = title,
                Farmed = self.State.Farmed + count }
        end, function(ok, result) self:FeatureResult("AutoFarm", ok, result) end)
    end
    for _, pair in ipairs({ { "AutoCollectOrbs", "orbs", "CollectedOrbs" },
        { "AutoCollectLootbags", "lootbags", "CollectedLootbags" } }) do
        local key, kind, field = pair[1], pair[2], pair[3]
        if self.Options[key] and not self.Jobs:busy(key) and now >= (self.NextAt[key] or 0) then
            self.NextAt[key] = now + 1
            self.Jobs:start(key, Config.RequestTimeout, function(activeJob)
                local count = self.Adapter:Collect(kind, self.Options.Radius, function()
                    return activeJob() and self.Alive and self.Options[key] and self.Player.Character == character
                        and character.Parent ~= nil and root.Parent ~= nil and humanoid.Parent ~= nil and humanoid.Health > 0
                end)
                return { [field] = self.State[field] + count }
            end, function(ok, result) self:FeatureResult(key, ok, result) end)
        end
    end
    if now >= (self.NextPublish or 0) then
        for _, key in ipairs({ "AutoFarm", "AutoCollectOrbs", "AutoCollectLootbags" }) do
            if self.Options[key] and self.Jobs:blocked(key) then
                self.State.Status = "Waiting for a canceled request to finish; no retry sent."
                break
            end
        end
        self.NextPublish = now + 1
        self:Publish()
    end
end

function Runtime:Publish()
    if not self.Alive then return end
    self.State.Options = table.clone(self.Options)
    self.State.WorkerStatus = self.Jobs:summary()
    self.State.ProbeStage = self.Adapter._phase or "not started"
    self.State.CareStage = self.Care._phase or "not started"
    self.State.Supported = table.clone(self.Adapter.Supported)
    for key, supported in pairs(self.Care.Supported) do self.State.Supported[key] = supported end
    for field, count in pairs(self.Care.Counts) do self.State[field] = count end
    self.State.Supported.AntiIdle = not self.AntiIdleUnavailable
    self.State.Capabilities = self.Adapter.Reason
        .. "\nNative Roblox UI; no external UI loader or hooks required."
        .. "\nIdle input and clipboard are tested only when used.\n" .. self.Care.Reason
    self.Ui:Update(self.State)
end

function Runtime:RestoreMovement()
    local saved = self.Movement
    self.Movement = nil
    if saved and saved.Humanoid.Parent then
        pcall(function()
            saved.Humanoid.WalkSpeed = saved.WalkSpeed
            saved.Humanoid.JumpPower = saved.JumpPower
            saved.Humanoid.JumpHeight = saved.JumpHeight
        end)
    end
end

function Runtime:ApplyMovement(humanoid)
    humanoid = humanoid or (self.Player.Character and self.Player.Character:FindFirstChildOfClass("Humanoid"))
    if not humanoid then return end
    if not self.Movement or self.Movement.Humanoid ~= humanoid then
        self:RestoreMovement()
        self.Movement = { Humanoid = humanoid, WalkSpeed = humanoid.WalkSpeed,
            JumpPower = humanoid.JumpPower, JumpHeight = humanoid.JumpHeight }
    end
    humanoid.WalkSpeed = self.Options.WalkSpeed
    if humanoid.UseJumpPower then
        humanoid.JumpPower = self.Options.JumpPower
    else
        humanoid.JumpHeight = self.Options.JumpPower ^ 2 / (2 * math.max(workspace.Gravity, 1))
    end
end

function Runtime:SetLighting(enabled)
    if enabled then
        if not self.Lighting then
            self.Lighting = {}
            for _, key in ipairs({ "Brightness", "ClockTime", "FogEnd", "GlobalShadows", "Ambient", "OutdoorAmbient" }) do
                self.Lighting[key] = Lighting[key]
            end
        end
        Lighting.Brightness = 2
        Lighting.ClockTime = 14
        Lighting.FogEnd = 100000
        Lighting.GlobalShadows = false
        Lighting.Ambient = Color3.fromRGB(180, 180, 180)
        Lighting.OutdoorAmbient = Color3.fromRGB(180, 180, 180)
    elseif self.Lighting then
        for key, value in pairs(self.Lighting) do pcall(function() Lighting[key] = value end) end
        self.Lighting = nil
    end
end

function Runtime:SetOption(key, value)
    if not self.Alive then return false, "Suite is unloaded." end
    local parsed, reason = Policy.option(key, value)
    if parsed == nil then return false, reason end
    if parsed == true and self.Adapter.Supported[key] == false then
        return false, self.Adapter.Reason
    end
    if parsed == true and self.Care.Supported[key] == false then return false, self.Care.Reason end
    if key == "ModulePathMode" and (self.Jobs:busy("connect") or self.Jobs:busy("care")
        or self.Ready or self.Care.Supported.AutoHatch or self.Care.Supported.AutoGold or self.Care.Supported.AutoRainbow) then
        return false, "Stop and rejoin before switching module paths; do not overlap native module calls."
    end
    if key == "AntiIdle" and parsed and self.AntiIdleUnavailable then
        return false, "This executor rejected idle input in this session."
    end
    local previous = self.Options[key]
    self.Options[key] = parsed
    if key == "HeavenIslandSweep" and parsed then
        return false, "Use START Heaven Island autofarm; do not use the legacy network toggle."
    end
    if key == "HeavenChestAssist" and not parsed then
        self.ChestArmAt, self.ChestClickedPart, self.ChestAnchorPosition = nil, nil, nil
        self.State.ChestStatus = "Stopped"
    end
    if type(parsed) == "boolean" then
        if not parsed then
            self.Jobs:cancel(key)
            if key == "AutoHatch" or key == "AutoGold" or key == "AutoRainbow" then
                self.Jobs:cancel("care")
                self.Navigator:Stop()
            end
            if key == "AutoFarm" or key == "WalkToTarget" then self:StopNavigation() end
        else
            self.Failures[key] = 0
            self.NextAt[key] = 0
        end
    end
    if key == "EggName" or key == "HatchMode" or key == "ConversionSpecies" or key == "MachineTravelMode" then
        self.Jobs:cancel("care")
        self.Navigator:Stop()
    end
    if key == "AutoFarm" or key == "FarmMode" or key == "Area" or key == "NameFilter" or key == "Radius" then
        self.Jobs:cancel("AutoFarm")
        self:StopNavigation()
        self.LastAssignment = nil
        self.Failures.AutoFarm = 0
        self.NextAt.AutoFarm = 0
    end
    local ok, message = pcall(function()
        if key == "MovementEnabled" then
            if parsed then self:ApplyMovement() else self:RestoreMovement() end
        elseif key == "WalkSpeed" or key == "JumpPower" then
            if self.Options.MovementEnabled then self:ApplyMovement() end
        elseif key == "Fullbright" then
            self:SetLighting(parsed)
        end
    end)
    if not ok then
        self.Options[key] = previous
        if key == "MovementEnabled" or key == "WalkSpeed" or key == "JumpPower" then
            self.Options.MovementEnabled = false
            self:RestoreMovement()
        elseif key == "Fullbright" then
            self.Options.Fullbright = false
            self:SetLighting(false)
        end
        self.State.LastError = tostring(message)
        self:Publish()
        return false, tostring(message)
    end
    self:Publish()
    return true
end

function Runtime:StopAll()
    self.Jobs:cancelAll()
    self.Navigator:Stop()
    self:StopNavigation()
    self.LastAssignment = nil
    self.NextAt = {}
    self.ChestArmAt, self.ChestClickedPart, self.ChestAnchorPosition = nil, nil, nil
    self.State.ChestStatus = "Stopped"
    self.HeavenSweepNextAt = nil
    self.State.HeavenSweepStatus = "Stopped (B to restart)"
    self.HeavenSweepPending = nil
    for key, value in pairs(self.Options) do
        if type(value) == "boolean" then self.Options[key] = false end
    end
    self:RestoreMovement()
    self:SetLighting(false)
    self.State.Status = "Stopped — all automation disabled"
    self.State.CareStatus = "Pet automation stopped"
    self:Publish()
end

function Runtime:InspectEnvironment()
    if not self.Alive then return false, "Suite unloaded." end
    if self.Jobs:busy("connect") then
        return false, "A compatibility check is still active. No parallel preflight was started."
    end
    local ok, ready, message = pcall(function() return self.Adapter:Inspect() end)
    if not ok then
        message = tostring(ready)
        ready = false
    end
    self.State.Status = if ready then "Local preflight passed — protocol not tested" else "Local preflight needs attention"
    self.State.LastError = if ready then "" else tostring(message)
    self:Publish()
    return ready, message
end

function Runtime:InspectCoinModels()
    if not self.Alive then return false, "Suite unloaded." end
    local ok, inspected, report = pcall(function() return self.Adapter:InspectCoinModels() end)
    if not ok then
        report, inspected = tostring(inspected), false
    end
    self.State.Status = if inspected
        then "Local coin models inspected; farming still requires a verified protocol"
        else "Local coin inspection unavailable"
    if not inspected then self.State.LastError = tostring(report) end
    self:Publish()
    return inspected, report
end

function Runtime:Reconnect()
    self:StopAll()
    self.Ready = false
    self.Adapter.Supported = { AutoFarm = false, AutoCollectOrbs = false, AutoCollectLootbags = false, WalkToTarget = false }
    if type(self.Adapter.Inspect) == "function" then
        local ok, ready, message = pcall(function() return self.Adapter:Inspect() end)
        if not ok or not ready then
            self.State.Status = "Local preflight failed; no network request sent"
            self.State.LastError = if ok then tostring(message) else tostring(ready)
            self:Publish()
            return false, self.State.LastError
        end
    end
    self.State.Status = "Checking Classic Event protocol..."
    self:Publish()
    local started = self.Jobs:start("connect", Config.RequestTimeout, function(activeJob)
        return self.Adapter:Connect(activeJob, self.Options.ModulePathMode)
    end, function(ok, message)
        self.Ready = ok and self.Adapter.Supported.AutoFarm == true
        self.State.Status = if self.Ready then "Protocol probe passed — enable a feature to test in game" else "Compatibility probe failed — see Status"
        self.State.LastError = if self.Ready then "" elseif not ok then tostring(message) .. " [Probe stage: " .. tostring(self.Adapter._phase or "unknown") .. "]" else self.Adapter.Reason
        self:Publish()
    end)
    if not started then
        self.State.Status = "Previous compatibility check is still returning; no new check sent."
        self:Publish()
        return false, self.State.Status
    end
    return true
end

function Runtime:Diagnostics()
    return table.concat({
        Config.Name .. " v" .. Config.Version,
        "Startup makes no game-module or network probe. The compatibility check is manual.",
        "Current PlaceId: " .. tostring(game.PlaceId) .. "; UniverseId: " .. tostring(game.GameId),
        "Current probe stage: " .. tostring(self.Adapter._phase or "not started"),
        "Current pet-tools stage: " .. tostring(self.Care._phase or "not started"),
        "Heaven chest input assist: " .. tostring(self.State.ChestStatus or "off")
            .. "; attempted clicks=" .. tostring(self.State.ChestClicks or 0),
        "Heaven Island target scan: " .. tostring(self.State.HeavenScanStatus or "not scanned")
            .. "; identifiable targets=" .. tostring(self.State.HeavenTargetCount or 0),
        "Heaven Island AutoFarm (B toggle): " .. tostring(self.State.HeavenSweepStatus or "off")
            .. "; clicks attempted=" .. tostring(self.State.HeavenSweepClicks or 0)
            .. "; off-target skips=" .. tostring(self.HeavenSweepMismatches or 0)
            .. "; input mode=" .. tostring(self.State.HeavenSweepMode or "not started"),
        "Selected module path: " .. tostring(self.Options.ModulePathMode),
        "Active workers:\n" .. self.Jobs:summary(),
        self.Adapter.Report,
        self.Care.Report,
        "Options: " .. HttpService:JSONEncode(self.Options),
        "Last error: " .. tostring(self.State.LastError),
        "Counters represent requests, not confirmed rewards. No credentials or inventory transfer is performed.",
    }, "\n")
end

function Runtime:Action(action)
    if action == "StopAll" then self:StopAll()
    elseif action == "Reconnect" then return self:Reconnect()
    elseif action == "ScanHeavenTargets" then return self:ScanHeavenTargets()
    elseif action == "StartHeavenSweep" then return self:StartHeavenSweep()
    elseif action == "StopHeavenSweep" then return self:StopHeavenSweep()
    elseif action == "ArmHeavenChest" then return self:ArmHeavenChest()
    elseif action == "StopHeavenChest" then return self:StopHeavenChest()
    elseif action == "InspectEnvironment" then return self:InspectEnvironment()
    elseif action == "InspectCoinModels" then return self:InspectCoinModels()
    elseif action == "PrepareCare" then return self:PrepareCare()
    elseif action == "InspectSave" then return self:InspectSave()
    elseif action == "NextEgg" or action == "NextSpecies" then
        local key = if action == "NextEgg" then "EggName" else "ConversionSpecies"
        local value, caption = self.Care:NextChoice(if action == "NextEgg" then "Egg" else "Species", self.Options[key])
        local accepted, reason = self:SetOption(key, value)
        if not accepted then return false, reason end
        self.State.CareStatus = "Selected " .. caption
        self:Publish()
    elseif action == "HatchOnce" then return self:StartCare("AutoHatch", true)
    elseif action == "GoldOnce" then return self:StartCare("AutoGold", true)
    elseif action == "RainbowOnce" then return self:StartCare("AutoRainbow", true)
    elseif action == "OpenEggMenu" then return self.Care:OpenMenu("Egg")
    elseif action == "GoGoldMachine" then return self:GoToMachine("Gold", false)
    elseif action == "GoRainbowMachine" then return self:GoToMachine("Rainbow", false)
    elseif action == "OpenGoldMenu" then
        if self.Options.MachineTravelMode == "Walk" then return self:GoToMachine("Gold", true) end
        return self.Care:OpenMenu("Gold")
    elseif action == "OpenRainbowMenu" then
        if self.Options.MachineTravelMode == "Walk" then return self:GoToMachine("Rainbow", true) end
        return self.Care:OpenMenu("Rainbow")
    elseif action == "OpenInventory" then return self.Care:OpenMenu("Inventory")
    elseif action == "ClearError" then self.State.LastError = ""; self:Publish()
    elseif action == "ResetMovement" then return self:SetOption("MovementEnabled", false)
    elseif action == "Unload" then self:Destroy()
    elseif action == "Rejoin" then
        self:StopAll()
        local ok, message = pcall(function()
            game:GetService("TeleportService"):Teleport(game.PlaceId, self.Player)
        end)
        if not ok then return false, tostring(message) end
    elseif action == "CopyDiagnostics" then
        local report = self:Diagnostics()
        local copy = setclipboard or toclipboard
        if type(copy) == "function" then
            local ok, message = pcall(copy, report)
            if ok then return true end
            self.State.LastError = "Clipboard failed: " .. tostring(message)
        end
        print(report)
        self:Publish()
        return false, "Clipboard unavailable; diagnostics printed to the console."
    else return false, "Unknown action." end
    return true
end

function Runtime:Destroy()
    if not self.Alive then return end
    self:StopAll()
    self.Alive = false
    if self.Pulse then pcall(task.cancel, self.Pulse) end
    for _, connection in ipairs(self.Connections) do connection:Disconnect() end
    self.Adapter:Destroy()
    self.Care:Destroy()
    self.Ui:Destroy()
    if self.OnDestroy then self.OnDestroy() end
end

return Runtime
