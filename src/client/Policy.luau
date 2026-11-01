--!strict
-- Pure targeting and settings rules; also executed by the standalone Luau tests.
local Policy = {}

local numeric = {
    Radius = { 10, 1000 },
    FarmInterval = { 0.25, 10 },
    WalkSpeed = { 8, 100 },
    JumpPower = { 0, 150 },
    HatchInterval = { 1, 30 },
    ConversionInterval = { 2, 30 },
}
local booleans = {
    AutoFarm = true,
    AutoCollectOrbs = true,
    AutoCollectLootbags = true,
    WalkToTarget = true,
    MovementEnabled = true,
    Fullbright = true,
    AntiIdle = true,
    AutoHatch = true,
    AutoGold = true,
    AutoRainbow = true,
}

function Policy.option(key: string, value: any): (any, string?)
    if booleans[key] then
        if type(value) == "boolean" then
            return value, nil
        end
        return nil, "Expected an on/off value."
    end
    local range = numeric[key]
    if range then
        local number = tonumber(value)
        if not number or number ~= number or math.abs(number) == math.huge then
            return nil, "Enter a finite number."
        end
        return math.clamp(number, range[1], range[2]), nil
    end
    if key == "ModulePathMode" then
        if value == "Facade" or value == "Direct" then return value, nil end
        return nil, "Choose Facade or Direct for module loading."
    end
    if key == "FarmMode" then
        if value == "Nearest" or value == "Weakest" or value == "Strongest" then
            return value, nil
        end
        return nil, "Unknown farm mode."
    end
    if key == "HatchMode" then
        if value == "Single" or value == "Triple" or value == "Octuple" then return value, nil end
        return nil, "Choose Single, Triple or Octuple."
    end
    if key == "MachineTravelMode" then
        if value == "Walk" or value == "Off" then return value, nil end
        return nil, "Choose Walk or Off for machine travel."
    end
    if key == "Area" or key == "NameFilter" or key == "EggName" or key == "ConversionSpecies" then
        if type(value) ~= "string" then
            return nil, "Expected text."
        end
        local text = string.sub(value, 1, 100):match("^%s*(.-)%s*$") or ""
        if key == "Area" and text == "" then
            text = "All"
        end
        return text, nil
    end
    return nil, "Unknown setting: " .. tostring(key)
end

function Policy.select(candidates: { any }, options: any): any
    local selected = nil
    local filter = string.lower(options.NameFilter)
    local area = string.lower(options.Area)
    for _, item in ipairs(candidates) do
        local valid = item.health > 0
            and item.distance <= options.Radius
            and (area == "all" or string.lower(item.area) == area)
            and (filter == "" or string.find(string.lower(item.name), filter, 1, true) ~= nil)
        if not valid then
            continue
        end
        local better = selected == nil
        if selected then
            if options.FarmMode == "Weakest" and item.health ~= selected.health then
                better = item.health < selected.health
            elseif options.FarmMode == "Strongest" and item.health ~= selected.health then
                better = item.health > selected.health
            elseif item.distance ~= selected.distance then
                better = item.distance < selected.distance
            else
                better = tostring(item.id) < tostring(selected.id)
            end
        end
        if better then
            selected = item
        end
    end
    return selected
end

return Policy
