--!nocheck
-- Native public-library integration. Legacy signatures are not live-event proof.
local Config = require(script.Parent.Config)
local ConversionPolicy = require(script.Parent.ConversionPolicy)
local PetCare = {}
PetCare.__index = PetCare

local function none()
    return { AutoHatch = false, AutoGold = false, AutoRainbow = false }
end
local function text(value) return type(value) == "string" and value:match("%S") ~= nil end
local function number(value) return type(value) == "number" and value == value and math.abs(value) < math.huge end
local function child(parent, name) return parent and parent:FindFirstChild(name) end
local function samePlace() return game.PlaceId == Config.Target.PlaceId and game.GameId == Config.Target.UniverseId end

function PetCare.new()
    return setmetatable({ Supported = none(), Reason = "Pet tools idle — click Load pet tools.",
        Report = "Pet tools not loaded.", Counts = { HatchRequests = 0, GoldRequests = 0, RainbowRequests = 0 },
        _generation = 0, _destroyed = false, _reserved = {}, _menus = {} }, PetCare)
end

function PetCare:_report()
    self.Report = "Pet stage: " .. tostring(self._phase or "not started") .. "\nPet tools: " .. self.Reason .. "\nPet-tool loader: " .. (self._loader or "not selected")
        .. "\nPet-tool provider: ReplicatedStorage.Library (public). Legacy commands; current game acceptance unverified."
        .. "\nConversion: exactly six; explicit species; loaded unlocked inventory slots required."
        .. "\nRequests are counted, not confirmed hatches or conversion rewards."
end

function PetCare:_occupied()
    if self._busy and coroutine.status(self._busy) == "dead" then self._busy = nil end
    return self._busy ~= nil
end

function PetCare:Connect(active)
    if self:_occupied() then error("A pet-tool operation is still returning. Stop it and wait before loading again.", 0) end
    if active and not active() then return self end
    self._generation += 1
    local generation = self._generation
    local function current() return self._generation == generation and not self._destroyed and (not active or active()) end
    self.Supported, self._api = none(), nil
    self._phase = "Checking game and public Library"
    self:_report()
    local ok, message = pcall(function()
        if self._destroyed then error("Pet tools unloaded.", 0) end
        if not samePlace() then error("Load pet tools inside the Classic Event destination.", 0) end
        local library = game:GetService("ReplicatedStorage"):FindFirstChild("Library")
        if not library or not library:IsA("ModuleScript") then error("Public Library ModuleScript is not loaded.", 0) end
        local loader, loaderName = require, "require"
        if type(getrenv) == "function" then
            local available, environment = pcall(getrenv)
            if available and type(environment) == "table" and type(environment.require) == "function" then
                loader, loaderName = environment.require, "getrenv().require"
            end
        end
        if not current() then return end
        self._loader = loaderName
        self._phase = "Loading pet API facade"
        self:_report()
        local facade = loader(library)
        if not current() then return end
        if type(facade) ~= "table" then error("Public Library did not return a table.", 0) end
        self._phase = "Reading public Library.Network"
        self:_report()
        local network = facade.Network
        if not current() then return end
        local invoke = type(network) == "table" and network.Invoke
        if not current() then return end
        self._phase = "Reading public Library.Save"
        self:_report()
        local save = facade.Save
        if not current() then return end
        local getSave = type(save) == "table" and save.Get
        if not current() then return end
        self._phase = "Reading public Library.PetCmds"
        self:_report()
        local pets = facade.PetCmds
        if not current() then return end
        local getEquipped = type(pets) == "table" and pets.GetEquipped
        if not current() then return end
        self._phase = "Reading public Library.Directory"
        self:_report()
        local directory = facade.Directory
        if not current() then return end
        local eggDirectory = type(directory) == "table" and directory.Eggs
        if not current() then return end
        local petDirectory = type(directory) == "table" and directory.Pets
        if not current() then return end
        if type(invoke) ~= "function" or type(getSave) ~= "function" then
            error("Public Network.Invoke / Save.Get unavailable. No private networking fallback attempted.", 0)
        end
        self._phase = "Pet API exports validated"
        self:_report()
        self._api = { invoke = invoke, getSave = getSave, getEquipped = getEquipped,
            eggs = eggDirectory, pets = petDirectory }
        self._loader = loaderName
        self.Supported.AutoHatch = type(eggDirectory) == "table"
        local conversion = type(petDirectory) == "table" and type(getEquipped) == "function"
        self.Supported.AutoGold, self.Supported.AutoRainbow = conversion, conversion
        self.Reason = "Pet APIs loaded; no remote probe sent. Server decides access, hatch modes and conversion chances."
    end)
    if not current() then return self end
    if not ok then self.Reason = tostring(message) end
    self:_report()
    return self
end

function PetCare:_run(key, active, work)
    if active and not active() then return 0 end
    if self._destroyed or not samePlace() or not self._api or not self.Supported[key] then error(self.Reason, 0) end
    if self:_occupied() then error("Another pet operation is still returning; no overlapping request sent.", 0) end
    local generation = self._generation
    local function current() return not self._destroyed and generation == self._generation and samePlace() and (not active or active()) end
    local owner = coroutine.running()
    self._busy = owner
    local ok, result = pcall(work, current)
    if self._busy == owner then self._busy = nil end
    if not current() then return 0 end
    if not ok then error(result, 0) end
    return result
end

function PetCare:_request(key, command, counter, current, ...)
    if not current() then return 0 end
    self._lastFailure = nil
    self._phase = "Waiting for " .. command .. " acknowledgement"
    self:_report()
    self.Counts[counter] += 1
    local response = table.pack(pcall(self._api.invoke, command, ...))
    if not current() then return 0 end
    self._phase = "Validating " .. command .. " reply"
    self:_report()
    if not response[1] or response.n < 2 or response[2] ~= true then
        local message
        if not response[1] then message = tostring(response[2])
        elseif response[2] == false and type(response[3]) == "string" then message = response[3] end
        if message then message = message:sub(1, 500):gsub("[%c]", " ") end
        local distance = response[1] and response[2] == false and message
            and message:lower():find("too far", 1, true) ~= nil
        self._lastFailure = if distance then "Distance" else "Unknown"
        -- A definite range rejection is recoverable after approaching normally.
        self.Supported[key] = distance == true
        self.Reason = command .. ": " .. (message or "No true acknowledgement returned.")
            .. (if distance then " Move closer to the target in game, then retry. No automatic retry was sent."
                else " Feature stopped; inspect the error before loading again.")
        self:_report()
        error(self.Reason, 0)
    end
    self.Reason = command .. " acknowledged. Request count does not confirm the resulting pets."
    self:_report()
    return 1
end

function PetCare:Hatch(eggName, mode, active)
    return self:_run("AutoHatch", active, function(current)
        if not text(eggName) then error("Enter an exact egg directory name first.", 0) end
        local count = if mode == "Single" then 1 elseif mode == "Triple" then 3 elseif mode == "Octuple" then 8 else nil
        if not count then error("Choose Single, Triple or Octuple hatch mode.", 0) end
        local egg = self._api.eggs[eggName]
        if not current() then return 0 end
        if type(egg) ~= "table" or egg.hatchable ~= true or egg.disabled or egg.isPremium
            or not text(egg.currency) or egg.currency:lower() == "robux" or not number(egg.cost) or egg.cost <= 0 then
            error("Unknown, unavailable or premium egg. Select a hatchable in-game currency egg.", 0)
        end
        local save = self._api.getSave()
        if not current() then return 0 end
        if type(save) ~= "table" or not number(save[egg.currency]) or save[egg.currency] < egg.cost * count then
            error("Insufficient or unreadable " .. egg.currency .. " balance for this hatch mode.", 0)
        end
        return self:_request("AutoHatch", "Buy Egg", "HatchRequests", current, eggName, mode == "Triple", mode == "Octuple")
    end)
end

local function speciesId(directory, selected)
    if not text(selected) then error("Choose one conversion species by exact name or ID first.", 0) end
    if type(directory[selected]) == "table" then return selected, directory[selected] end
    local numeric = tonumber(selected)
    if numeric and type(directory[numeric]) == "table" then return tostring(numeric), directory[numeric] end
    local found
    for id, definition in pairs(directory) do
        if type(definition) == "table" and type(definition.name) == "string" and definition.name:lower() == selected:lower() then
            if found then error("Species name is ambiguous; enter its exact directory ID.", 0) end
            found = tostring(id)
        end
    end
    if not found then error("No pet directory entry matches this species.", 0) end
    return found, directory[found] or directory[tonumber(found)]
end

function PetCare:NextChoice(kind, previous)
    if self._destroyed or not samePlace() or not self._api then error("Load pet tools first.", 0) end
    local choices = {}
    local directory = if kind == "Egg" then self._api.eggs elseif kind == "Species" then self._api.pets else nil
    if type(directory) ~= "table" then error("This directory is unavailable.", 0) end
    for id, definition in pairs(directory) do
        if type(definition) ~= "table" then continue end
        local eligible
        if kind == "Egg" then
            eligible = definition.hatchable == true and not definition.disabled and not definition.isPremium
                and text(definition.currency) and definition.currency:lower() ~= "robux" and number(definition.cost) and definition.cost > 0
        else
            eligible = text(definition.rarity) and not definition.isPremium and not definition.isGift and not definition.huge and not definition.titanic
                and definition.rarity ~= "Exclusive" and definition.rarity ~= "Event"
        end
        if eligible and (text(id) or number(id)) then
            table.insert(choices, { value = tostring(id), label = if kind == "Species" and text(definition.name)
                then definition.name .. " (" .. tostring(id) .. ")" else tostring(id) })
        end
    end
    table.sort(choices, function(a, b) return a.value < b.value end)
    if #choices == 0 then error("No eligible entries are loaded in this directory.", 0) end
    local index = 0
    for i, choice in ipairs(choices) do if choice.value == previous then index = i; break end end
    local nextChoice = choices[index % #choices + 1]
    return nextChoice.value, nextChoice.label
end

local function unlockedSlot(playerGui, uid)
    local slots = child(child(child(child(playerGui, "Inventory"), "Frame"), "Main"), "Pets")
    local normal = child(slots, "Normal")
    local slot = child(normal, uid)
    local locked = child(slot, "Locked")
    if not slot or not slot:IsA("TextButton") or not locked or locked.Visible ~= false then return false end
    local favorite = child(slot, "Favorite") or child(slot, "Favourite")
    return not favorite or favorite.Visible == false
end

function PetCare:_conversionBatch(variant, selected, current)
    local id, definition = speciesId(self._api.pets, selected)
    if not current() then return nil end
    if type(definition) ~= "table" or not text(definition.rarity) then error("Unknown species metadata.", 0) end
    local premium = definition.isPremium or definition.isGift or definition.huge or definition.titanic
        or definition.rarity == "Exclusive" or definition.rarity == "Event"
    local save = self._api.getSave()
    if not current() then return nil end
    if type(save) ~= "table" or type(save.Pets) ~= "table" then error("Save.Get did not provide a Pets table.", 0) end
    local equipped = self._api.getEquipped()
    if not current() then return nil end
    if type(equipped) ~= "table" then error("Equipped pet records are unreadable; conversion stopped.", 0) end
    local worn = {}
    for _, pet in pairs(equipped) do
        if type(pet) ~= "table" or not text(pet.uid) then error("Unknown equipped-pet schema.", 0) end
        worn[pet.uid] = true
    end
    local normalized, present = {}, {}
    local player = game:GetService("Players").LocalPlayer
    local gui = player and player:FindFirstChild("PlayerGui")
    for _, pet in pairs(save.Pets) do
        if type(pet) ~= "table" or not text(pet.uid) or (type(pet.id) ~= "string" and type(pet.id) ~= "number") then
            error("Unknown inventory pet schema; no conversion sent.", 0)
        end
        present[pet.uid] = true
        local protected = premium or self._reserved[pet.uid] or false
        for _, flag in ipairs({ "g", "r", "dm", "hc", "sh", "l", "lk", "locked", "favorite", "fav" }) do
            if pet[flag] ~= nil and type(pet[flag]) ~= "boolean" then protected = true end
        end
        protected = protected or pet.dm or pet.hc or pet.sh or pet.l or pet.lk or pet.locked or pet.favorite or pet.fav
            or (text(pet.nk)) or (type(pet.e) == "table" and next(pet.e) ~= nil)
        local unlocked = unlockedSlot(gui, pet.uid)
        table.insert(normalized, { uid = pet.uid, species = tostring(pet.id),
            variant = if pet.r then "Rainbow" elseif pet.g then "Gold" else "Normal",
            protected = protected == true, equipped = worn[pet.uid] == true,
            eligible = tostring(pet.id) == id and unlocked and not protected })
    end
    if not current() then return nil end
    for uid in pairs(self._reserved) do if not present[uid] then self._reserved[uid] = nil end end
    local batch, reason = ConversionPolicy.NextBatch(normalized, variant)
    if not batch then
        self.Reason = (reason or "No eligible batch.") .. " Open Inventory to load lock indicators; select one species."
        self:_report()
        return nil
    end
    if not current() then return nil end
    return batch
end

function PetCare:CanConvert(variant, selected, active)
    local key = if variant == "Gold" then "AutoGold" elseif variant == "Rainbow" then "AutoRainbow" else nil
    if not key then error("Choose Gold or Rainbow conversion.", 0) end
    local result = self:_run(key, active, function(current)
        local batch = self:_conversionBatch(variant, selected, current)
        return batch ~= nil and current()
    end)
    return result == true
end

function PetCare:Convert(variant, selected, active)
    local key = if variant == "Gold" then "AutoGold" elseif variant == "Rainbow" then "AutoRainbow" else nil
    if not key then error("Choose Gold or Rainbow conversion.", 0) end
    return self:_run(key, active, function(current)
        local batch = self:_conversionBatch(variant, selected, current)
        if not batch or not current() then return 0 end
        -- Reserve before the request: an uncertain/late reply must never replay UIDs.
        for _, uid in ipairs(batch) do self._reserved[uid] = true end
        local ok, result = pcall(self._request, self, key,
            if variant == "Gold" then "Use Golden Machine" else "Use Rainbow Machine",
            if variant == "Gold" then "GoldRequests" else "RainbowRequests", current, batch)
        if not ok then
            if current() and self._lastFailure == "Distance" then
                for _, uid in ipairs(batch) do self._reserved[uid] = nil end
            end
            error(result, 0)
        end
        return result
    end)
end

function PetCare:OpenMenu(kind)
    if self._destroyed then error("Pet tools unloaded.", 0) end
    local names = { Gold = "Golden", Rainbow = "Rainbow", Inventory = "Inventory", Egg = "Eggs" }
    local player = game:GetService("Players").LocalPlayer
    local gui = player and player:FindFirstChild("PlayerGui")
    local menu = names[kind] and child(gui, names[kind])
    if not menu or not menu:IsA("ScreenGui") then error("That native game menu is not loaded. Open it normally once, then retry.", 0) end
    if self._menus[menu] == nil then self._menus[menu] = menu.Enabled end
    menu.Enabled = true
    return true
end

function PetCare:Destroy()
    self._generation += 1
    self._destroyed, self._api, self.Supported = true, nil, none()
    for menu, enabled in pairs(self._menus) do if menu.Parent then pcall(function() menu.Enabled = enabled end) end end
    table.clear(self._menus)
end

return PetCare
