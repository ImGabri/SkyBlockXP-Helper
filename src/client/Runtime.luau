--!nocheck
local Config = require(script.Parent.Config)
local Policy = require(script.Parent.Policy)
local Jobs = require(script.Parent.Jobs)
local Interface = require(script.Parent.Interface)
local PetSim99 = require(script.Parent.PetSim99)
local PetCare = require(script.Parent.PetCare)

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
    self.Ui = Interface.mount({
        parent = parent, name = Config.Name, version = Config.Version, options = self.Options,
        onChange = function(key, value) return self:SetOption(key, value) end,
        onAction = function(action) return self:Action(action) end,
    })
    table.insert(self.Connections, player.CharacterAdded:Connect(function(character)
        for _, key in ipairs({ "AutoFarm", "AutoCollectOrbs", "AutoCollectLootbags" }) do self.Jobs:cancel(key) end
        self.Jobs:cancel("care")
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
    table.insert(self.Connections, game:GetService("TeleportService").TeleportInitFailed:Connect(function(who, _, message)
        if who == player and self.Alive then
            self.State.LastError = "Rejoin failed: " .. tostring(message)
            self:Publish()
        end
    end))
    self:Publish()
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
    local started = self.Jobs:start("care", Config.RequestTimeout, function(activeJob)
        return self.Care:Connect(activeJob)
    end, function(ok, result)
        self.State.CareStatus = if ok then self.Care.Reason else "Pet tools failed to load"
        self.State.LastError = if ok then "" else tostring(result)
        self:Publish()
    end)
    if not started then return false, "A previous pet operation is still returning; no new request sent." end
    self:Publish()
    return true
end

function Runtime:StartCare(key, manual)
    if not self.Alive then return false, "Suite unloaded." end
    if not self.Care.Supported[key] then return false, self.Care.Reason end
    local character = self.Player.Character
    if not character or not character.Parent then return false, "Wait for your character to load." end
    local egg, mode, species = self.Options.EggName, self.Options.HatchMode, self.Options.ConversionSpecies
    local started = self.Jobs:start("care", Config.RequestTimeout, function(activeJob)
        local function current()
            return self.Alive and activeJob() and self.Player.Character == character and character.Parent ~= nil
                and (manual or self.Options[key])
        end
        if key == "AutoHatch" then return self.Care:Hatch(egg, mode, current) end
        return self.Care:Convert(if key == "AutoGold" then "Gold" else "Rainbow", species, current)
    end, function(ok, result)
        self.State.CareStatus = self.Care.Reason
        if not ok then
            self.Options[key] = false
            self.State.LastError = key .. ": " .. tostring(result)
            self.State.CareStatus = "Pet operation stopped — see error"
        end
        self:Publish()
    end)
    if not started then return false, "A pet operation is still returning; no overlapping request sent." end
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
    self:StepCare()
    if not self.Ready then return end
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
            return { Status = if count > 0 then "Farm requests sent; waiting for game response." else "No additional pet dispatches needed.", Target = title,
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
    if key == "AntiIdle" and parsed and self.AntiIdleUnavailable then
        return false, "This executor rejected idle input in this session."
    end
    local previous = self.Options[key]
    self.Options[key] = parsed
    if type(parsed) == "boolean" then
        if not parsed then
            self.Jobs:cancel(key)
            if key == "AutoHatch" or key == "AutoGold" or key == "AutoRainbow" then self.Jobs:cancel("care") end
            if key == "AutoFarm" or key == "WalkToTarget" then self:StopNavigation() end
        else
            self.Failures[key] = 0
            self.NextAt[key] = 0
        end
    end
    if key == "EggName" or key == "HatchMode" or key == "ConversionSpecies" then
        self.Jobs:cancel("care")
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
    self:StopNavigation()
    self.LastAssignment = nil
    self.NextAt = {}
    for key, value in pairs(self.Options) do
        if type(value) == "boolean" then self.Options[key] = false end
    end
    self:RestoreMovement()
    self:SetLighting(false)
    self.State.Status = "Stopped — all automation disabled"
    self.State.CareStatus = "Pet automation stopped"
    self:Publish()
end

function Runtime:Reconnect()
    self:StopAll()
    self.Ready = false
    self.Adapter.Supported = { AutoFarm = false, AutoCollectOrbs = false, AutoCollectLootbags = false, WalkToTarget = false }
    self.State.Status = "Checking Classic Event protocol..."
    self:Publish()
    local started = self.Jobs:start("connect", Config.RequestTimeout, function(activeJob)
        return self.Adapter:Connect(activeJob)
    end, function(ok, message)
        self.Ready = ok and self.Adapter.Supported.AutoFarm == true
        self.State.Status = if self.Ready then "Protocol probe passed — enable a feature to test in game" else "Compatibility probe failed — see Status"
        self.State.LastError = if self.Ready then "" elseif not ok then tostring(message) else self.Adapter.Reason
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
    elseif action == "PrepareCare" then return self:PrepareCare()
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
    elseif action == "OpenGoldMenu" then return self.Care:OpenMenu("Gold")
    elseif action == "OpenRainbowMenu" then return self.Care:OpenMenu("Rainbow")
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
