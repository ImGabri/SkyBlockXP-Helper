--!nocheck
-- Experimental legacy coin protocol; current Classic Event support requires a live probe.
-- Native module access only. No hooks, upvalues, or authentication bypasses.
local PetSim99 = {}
PetSim99.__index = PetSim99
local Config = require(script.Parent.Config)

local function supportedNone()
    return { AutoFarm = false, AutoCollectOrbs = false, AutoCollectLootbags = false, WalkToTarget = false }
end

local function finite(value)
    return type(value) == "number" and value == value and value > -math.huge and value < math.huge
end

local function identifier(value)
    return (type(value) == "string" and value ~= "") or finite(value)
end

local function vector(value)
    return typeof(value) == "Vector3" and finite(value.X) and finite(value.Y) and finite(value.Z)
end

local function childSummary(parent, limit)
    if not parent then return "not present" end
    local names = {}
    for _, child in ipairs(parent:GetChildren()) do
        table.insert(names, child.Name .. " (" .. child.ClassName .. ")")
    end
    table.sort(names)
    local total = #names
    while #names > limit do table.remove(names) end
    local result = table.concat(names, ", ")
    if total > limit then result ..= string.format(" ... (%d more)", total - limit) end
    return if result == "" then "empty" else result
end

local function selectLoader()
    if type(getrenv) == "function" then
        local ok, environment = pcall(getrenv)
        if ok and type(environment) == "table" and type(environment.require) == "function" then
            return environment.require, "getrenv().require"
        end
    end
    return require, "require"
end

local function requireModule(module, path, loader)
    if not module or not module:IsA("ModuleScript") then
        error(path .. " is not an available ModuleScript. Reconnect after the event finishes loading.", 0)
    end
    local ok, value = pcall(loader or require, module)
    if not ok then
        error("Native require of " .. path .. " failed: " .. tostring(value)
            .. ". Module access may be unsupported by this executor; no bypass is attempted.", 0)
    end
    if type(value) ~= "table" then error(path .. " returned an unsupported value; expected a table.", 0) end
    return value
end

local function responseSummary(result)
    local types = {}
    for index = 1, result.n do table.insert(types, typeof(result[index])) end
    return "returns=" .. tostring(result.n) .. "; types=" .. (if #types > 0 then table.concat(types, ",") else "none")
end

local function exportSummary(exports, expected)
    local names = {}
    local keys = {}
    for name, value in pairs(exports) do
        if type(name) == "string" then keys[name] = true end
    end
    for _, name in ipairs(expected or {}) do keys[name] = true end
    for name in pairs(keys) do
        local readable, value = pcall(function() return exports[name] end)
        local shape = if readable then typeof(value) else "unavailable"
        if readable and type(value) == "function" and debug and type(debug.info) == "function" then
            local ok, count, variadic = pcall(debug.info, value, "a")
            if ok then shape ..= "(args=" .. tostring(count) .. ",variadic=" .. tostring(variadic) .. ")" end
        end
        table.insert(names, name .. ":" .. shape)
    end
    table.sort(names)
    while #names > 40 do table.remove(names) end
    return table.concat(names, ", ")
end

local function physicalPosition(instance)
    if instance:IsA("BasePart") then return instance.Position end
    if instance:IsA("Model") then
        local part = instance.PrimaryPart or instance:FindFirstChildWhichIsA("BasePart", true)
        if part then return part.Position end
    end
    return nil
end

function PetSim99.new()
    return setmetatable({
        Supported = supportedNone(),
        Reason = "Not connected. Reconnect inside the Classic Event to test the experimental coin protocol.",
        Report = "Not inspected yet.",
        _connected = false, _destroyed = false, _generation = 0,
        _cooldowns = setmetatable({}, { __mode = "k" }), _assigned = {},
        _counts = { FarmDispatches = 0, OrbIds = 0, LootbagIds = 0 },
    }, PetSim99)
end

function PetSim99:_report()
    self.Report = (self._diagnostics or "Not inspected yet.") .. "\nAdapter: " .. self.Reason
        .. "\nGet Coins response: " .. (self._coinResponse or "not called")
        .. "\nModule loader: " .. (self._loaderName or "not selected")
        .. "\nNetwork provider: " .. (self._networkProvider or "not selected")
        .. "\nNetwork exports: " .. (self._networkExports or "not loaded")
        .. "\nPetCmds exports: " .. (self._petExports or "not loaded")
        .. string.format("\nRequests only: %d pet farm dispatches; %d orb IDs; %d lootbag IDs. No collection/break confirmation is inferred.",
            self._counts.FarmDispatches, self._counts.OrbIds, self._counts.LootbagIds)
end

function PetSim99:_block(message)
    self._connected = false
    self.Supported = supportedNone()
    self.Reason = tostring(message)
    self:_report()
end

function PetSim99:_fail(message)
    self:_block(message)
    error(message, 0)
end

function PetSim99:_root()
    local player = game:GetService("Players").LocalPlayer
    local character = player and player.Character
    local root = character and character:FindFirstChild("HumanoidRootPart")
    if not root or not root:IsA("BasePart") or not vector(root.Position) then
        error("The character's HumanoidRootPart is unavailable. Wait for respawn and reconnect.", 0)
    end
    return root
end

function PetSim99:_call(method, command, ...)
    local generation = self._generation
    local outcome = table.pack(pcall(self._network[method], command, ...))
    if not outcome[1] then
        error(command .. " failed: " .. tostring(outcome[2])
            .. ". The event protocol or module access may differ; no bypass is attempted.", 0)
    end
    local result = table.pack(table.unpack(outcome, 2, outcome.n))
    if command == "Get Coins" and generation == self._generation and not self._destroyed then
        self._coinResponse = responseSummary(result)
    end
    if result[1] == false then error(command .. " was explicitly rejected by the game.", 0) end
    return table.unpack(result, 1, result.n)
end

function PetSim99:_readSnapshot(probe, active)
    local generation = self._generation
    local function current()
        return generation == self._generation and not self._destroyed and (not active or active())
    end
    if not current() then error("Coin read canceled before networking.", 0) end
    local returned = table.pack(self:_call("Invoke", "Get Coins"))
    local records = if returned.n == 1 then returned[1] else nil
    -- Status+payload responses must pass the same concrete coin validation.
    if returned.n == 2 and returned[1] == true and type(returned[2]) == "table" then
        records = returned[2]
    end
    if not current() then error("Coin read canceled by timeout, reconnect or unload.", 0) end
    local root = self:_root()
    if returned.n == 0 then
        error("Get Coins returned no values (returns=0; types=none). This native route provided no coin data. Inspect Network._check warnings and rejoin before another manual probe.", 0)
    end
    if type(records) ~= "table" then
        error("Get Coins returned an unsupported response (" .. responseSummary(returned)
            .. "); expected a coin dictionary or true plus a coin dictionary. A nil/empty reply does not establish compatibility.", 0)
    end
    if probe and next(records) == nil then
        error("Get Coins returned no records. Stand near loaded Classic Event coins and reconnect.", 0)
    end
    local candidates, assignments = {}, {}
    local allHealthKnown = true
    for id, raw in pairs(records) do
        if not identifier(id) or type(raw) ~= "table" or not vector(raw.p)
            or type(raw.a) ~= "string" or type(raw.n) ~= "string"
            or (raw.health ~= nil and (not finite(raw.health) or raw.health < 0)) then
            error("Get Coins returned an unknown coin schema. Farming is disabled rather than guessing a wrapper or field mapping.", 0)
        end
        local instance = self._coins:FindFirstChild(tostring(id))
        local coinPart = instance and instance:FindFirstChild("Coin")
        local areaAllowed = true
        if self._world and type(self._world.HasArea) == "function" then
            local ok, allowed = pcall(self._world.HasArea, raw.a)
            if not ok then error("WorldCmds.HasArea failed; reconnect before farming: " .. tostring(allowed), 0) end
            areaAllowed = allowed == true
        end
        if instance and instance:IsA("Model") and coinPart and coinPart:IsA("BasePart") and areaAllowed then
            local healthKnown = raw.health ~= nil
            allHealthKnown = allHealthKnown and healthKnown
            table.insert(candidates, {
                id = id, name = raw.n, area = raw.a,
                health = if healthKnown then raw.health else 1,
                healthKnown = healthKnown,
                distance = (root.Position - raw.p).Magnitude,
                position = raw.p, instance = instance,
            })
            local assigned = {}
            if type(raw.pets) == "table" then
                for _, uid in pairs(raw.pets) do
                    if identifier(uid) then assigned[tostring(uid)] = true end
                end
            end
            assignments[tostring(id)] = assigned
        end
    end
    if probe and #candidates == 0 then
        error("No valid Get Coins record matches a loaded __THINGS.Coins model with a Coin BasePart. Stand near event coins and reconnect.", 0)
    end
    if not current() then error("Pet read canceled before module access.", 0) end
    local ok, equipped = pcall(self._petCmds.GetEquipped)
    if not current() then error("Pet read canceled by timeout, reconnect or unload.", 0) end
    if not ok then error("PetCmds.GetEquipped failed: " .. tostring(equipped), 0) end
    if type(equipped) ~= "table" then error("PetCmds.GetEquipped returned an unsupported value; expected pet records.", 0) end
    local pets, seen = {}, {}
    for _, pet in pairs(equipped) do
        if type(pet) ~= "table" or not identifier(pet.uid) then
            error("PetCmds.GetEquipped returned an unknown pet record; expected a uid field.", 0)
        end
        local key = tostring(pet.uid)
        if not seen[key] then
            seen[key] = true
            table.insert(pets, pet.uid)
        end
    end
    self._assigned = assignments
    return { Candidates = candidates, Pets = pets, HealthKnown = #candidates > 0 and allHealthKnown }
end

function PetSim99:Connect(active)
    if active and not active() then return self end
    self._generation += 1
    local generation = self._generation
    local function current()
        return generation == self._generation and not self._destroyed and (not active or active())
    end
    self._destroyed, self._connected = false, false
    self.Supported = supportedNone()
    self._network, self._petCmds, self._world, self._coins, self._things = nil, nil, nil, nil, nil
    self._assigned = {}
    self._coinResponse, self._networkExports, self._petExports = nil, nil, nil
    self._moduleLoader, self._loaderName, self._networkProvider = nil, nil, nil
    self._cooldowns = setmetatable({}, { __mode = "k" })
    local matches = game.PlaceId == Config.Target.PlaceId and game.GameId == Config.Target.UniverseId
    local storage = game:GetService("ReplicatedStorage")
    local library = storage:FindFirstChild("Library")
    local client = library and library:FindFirstChild("Client")
    local things = workspace:FindFirstChild("__THINGS")
    self._diagnostics = table.concat({
        "Target: PS99 Classic Event (not legacy standalone PSX)",
        "PlaceId: " .. tostring(game.PlaceId),
        "UniverseId: " .. tostring(game.GameId),
        "Observed event destination: " .. (if matches then "MATCH" else "DIFFERENT PLACE/UNIVERSE"),
        "ReplicatedStorage: " .. childSummary(storage, 50),
        "Library: " .. childSummary(library, 80),
        "Library.Client: " .. childSummary(client, 120),
        "Framework: " .. childSummary(storage:FindFirstChild("Framework"), 50),
        "Network: " .. childSummary(storage:FindFirstChild("Network"), 100),
        "Workspace: " .. childSummary(workspace, 40),
        "__THINGS: " .. childSummary(things, 60),
        "__DEBRIS: " .. childSummary(workspace:FindFirstChild("__DEBRIS"), 40),
    }, "\n")
    local ok, message = pcall(function()
        if not matches then
            error("Enter Classic Event place " .. tostring(Config.Target.PlaceId) .. " in universe "
                .. tostring(Config.Target.UniverseId) .. " and reconnect. Current destination differs.", 0)
        end
        if not library then error("ReplicatedStorage.Library is not loaded. Wait inside the event and reconnect.", 0) end
        local loader, loaderName = selectLoader()
        if not current() then return end
        self._moduleLoader, self._loaderName = loader, loaderName
        local network, petCmds, world, networkPath
        if library:IsA("ModuleScript") then
            -- Use the documented public library rather than bypassing its facade.
            self._networkProvider = "ReplicatedStorage.Library"
            networkPath = "ReplicatedStorage.Library.Network"
            local facade = requireModule(library, "ReplicatedStorage.Library", loader)
            if not current() then return end
            network, petCmds = facade.Network, facade.PetCmds
            local ok, value = pcall(function() return facade.WorldCmds end)
            if ok then world = value end
            if type(network) ~= "table" or type(petCmds) ~= "table" then
                error("Public ReplicatedStorage.Library facade lacks Network/PetCmds tables. Internal client networking was not retried.", 0)
            end
        else
            -- Compatibility for legacy folder-only layouts; current event has a facade.
            if not client then error("Library.Client is not loaded. Wait inside the event and reconnect.", 0) end
            local networkModule = client:FindFirstChild("Network")
            networkPath = "Library.Client.Network"
            if not networkModule then
                networkModule = library:FindFirstChild("Network")
                networkPath = "Library.Network"
            end
            self._networkProvider = networkPath
            network = requireModule(networkModule, networkPath, loader)
            if not current() then return end
            petCmds = requireModule(client:FindFirstChild("PetCmds"), "Library.Client.PetCmds", loader)
            if not current() then return end
            local worldModule = client:FindFirstChild("WorldCmds")
            if worldModule and worldModule:IsA("ModuleScript") then
                local loaded, value = pcall(loader, worldModule)
                if not current() then return end
                if loaded then world = value end
            end
        end
        self._network, self._petCmds = network, petCmds
        self._networkExports = exportSummary(network, { "Invoke", "Fire" })
        self._petExports = exportSummary(petCmds, { "GetEquipped" })
        if type(self._network.Invoke) ~= "function" or type(self._network.Fire) ~= "function" then
            error(networkPath .. " lacks Invoke/Fire functions; this protocol is unsupported.", 0)
        end
        if type(self._petCmds.GetEquipped) ~= "function" then
            error("Library.Client.PetCmds lacks GetEquipped; this protocol is unsupported.", 0)
        end
        self._things = things
        self._coins = things and things:FindFirstChild("Coins")
        if not self._coins or not self._coins:IsA("Folder") then
            error("__THINGS.Coins is not an available Folder. Enter a loaded coin area and reconnect.", 0)
        end
        if type(world) == "table" and type(world.HasArea) == "function" then self._world = world end
        local snapshot = self:_readSnapshot(true, active)
        if not current() then return end
        self._connected = true
        self.Supported.AutoFarm, self.Supported.WalkToTarget = true, true
        local orbs = things:FindFirstChild("Orbs")
        local lootbags = things:FindFirstChild("Lootbags")
        self.Supported.AutoCollectOrbs = orbs ~= nil and orbs:IsA("Folder")
        self.Supported.AutoCollectLootbags = lootbags ~= nil and lootbags:IsA("Folder")
        self.Reason = string.format("Experimental legacy protocol probe passed (%d loaded coins, %d equipped pets); Classic Event farming still unverified in game.",
            #snapshot.Candidates, #snapshot.Pets)
    end)
    if not current() then return self end
    if not ok then self:_block(tostring(message)) end
    self:_report()
    return self
end

function PetSim99:Snapshot(active)
    if not self._connected or self._destroyed then error(self.Reason, 0) end
    local generation = self._generation
    local ok, result = pcall(self._readSnapshot, self, false, active)
    if generation ~= self._generation or self._destroyed or (active and not active()) then
        error("Snapshot canceled by timeout, reconnect or unload.", 0)
    end
    if not ok then self:_fail(tostring(result)) end
    return result
end

function PetSim99:Assign(target, pets, active)
    if not self._connected or self._destroyed then error(self.Reason, 0) end
    if type(target) ~= "table" or not identifier(target.id) or not target.instance then
        error("A loaded target from Snapshot is required.", 0)
    end
    local generation = self._generation
    local function current()
        return self._connected and not self._destroyed and generation == self._generation
            and target.instance.Parent == self._coins and (not active or active())
    end
    local count, seen = 0, {}
    local assigned = self._assigned[tostring(target.id)] or {}
    local ok, message = pcall(function()
        for _, uid in ipairs(pets) do
            if not current() then break end
            if not identifier(uid) then error("Equipped pet UID is invalid.", 0) end
            local key = tostring(uid)
            if not seen[key] and not assigned[key] then
                seen[key] = true
                self:_call("Invoke", "Join Coin", target.id, { uid })
                if not current() then break end
                self:_call("Fire", "Farm Coin", target.id, uid)
                count += 1
                self._counts.FarmDispatches += 1
                assigned[key] = true
                task.wait(0.15)
            end
        end
    end)
    self:_report()
    if not ok and current() then self:_fail(tostring(message)) end
    return count
end

function PetSim99:Collect(kind, radius, active)
    if not self._connected or self._destroyed then error(self.Reason, 0) end
    local folderName, command, limit, supportKey
    if kind == "orbs" then
        folderName, command, limit, supportKey = "Orbs", "Claim Orbs", 20, "AutoCollectOrbs"
    elseif kind == "lootbags" then
        folderName, command, limit, supportKey = "Lootbags", "Collect Lootbag", 4, "AutoCollectLootbags"
    else error("Unknown pickup kind; expected orbs or lootbags.", 0) end
    if not self.Supported[supportKey] then error(folderName .. " collection is unavailable.", 0) end
    if not finite(radius) then error("Pickup radius must be a finite number.", 0) end
    radius = math.clamp(radius, 0, 30)
    local generation = self._generation
    local function current()
        return self._connected and not self._destroyed and generation == self._generation and (not active or active())
    end
    local count = 0
    local ok, message = pcall(function()
        local folder = self._things:FindFirstChild(folderName)
        if not folder or not folder:IsA("Folder") then error(folderName .. " is no longer loaded. Reconnect.", 0) end
        local root = self:_root()
        local ids, objects, seen = {}, {}, {}
        for _, object in ipairs(folder:GetChildren()) do
            if not current() or #ids >= limit then break end
            local position = physicalPosition(object)
            local eligibleAt = self._cooldowns[object] or -math.huge
            if object.Parent == folder and vector(position) and (root.Position - position).Magnitude <= radius
                and os.clock() - eligibleAt >= 2 and object:GetAttribute("Collected") ~= true
                and object.Name ~= "" and not seen[object.Name] then
                seen[object.Name] = true
                table.insert(ids, object.Name)
                table.insert(objects, object)
            end
        end
        if #ids == 0 or not current() then return end
        if kind == "orbs" then
            self:_call("Fire", command, ids)
            count = #ids
            self._counts.OrbIds += count
            for _, object in ipairs(objects) do self._cooldowns[object] = os.clock() end
        else
            for index, object in ipairs(objects) do
                if not current() then break end
                root = self:_root()
                local position = physicalPosition(object)
                if object.Parent == folder and vector(position) and (root.Position - position).Magnitude <= radius then
                    self:_call("Fire", command, ids[index], root.Position)
                    self._cooldowns[object] = os.clock()
                    count += 1
                    self._counts.LootbagIds += 1
                    task.wait(0.15)
                end
            end
        end
    end)
    self:_report()
    if not ok and current() then self:_fail(tostring(message)) end
    return count
end

function PetSim99:Destroy()
    self._generation += 1
    self._destroyed = true
    self:_block("Adapter unloaded.")
    self._network, self._petCmds, self._world, self._coins, self._things = nil, nil, nil, nil, nil
    self._assigned = {}
    self._cooldowns = setmetatable({}, { __mode = "k" })
end

return PetSim99
