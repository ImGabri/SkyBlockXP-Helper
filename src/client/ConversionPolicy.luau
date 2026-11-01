--!strict
-- Pure selection over caller-normalized records, never raw game inventory.
-- The caller must establish eligibility and protection from a verified schema.
local ConversionPolicy = {}

local function text(value: any): boolean
    return type(value) == "string" and string.find(value, "%S") ~= nil
end

function ConversionPolicy.NextBatch(pets: any, targetVariant: any): ({ string }?, string?)
    local sourceVariant = if targetVariant == "Gold" then "Normal"
        elseif targetVariant == "Rainbow" then "Gold" else nil
    if not sourceVariant then
        return nil, "Choose Gold or Rainbow conversion."
    end
    if type(pets) ~= "table" then
        return nil, "Expected a normalized pet array."
    end
    local size = #pets
    for key in pairs(pets) do
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 or key > size then
            return nil, "Expected a dense normalized pet array."
        end
    end
    for index = 1, size do
        if pets[index] == nil then return nil, "Expected a dense normalized pet array." end
    end

    -- Duplicate identifiers invalidate every record with that UID, including
    -- an otherwise eligible record duplicated by a protected/malformed record.
    local occurrences: { [string]: number } = {}
    for _, pet in ipairs(pets) do
        if type(pet) ~= "table" then continue end
        local record = pet :: { [string]: any }
        if text(record.uid) then
            occurrences[record.uid] = (occurrences[record.uid] or 0) + 1
        end
    end
    local groups: { [string]: { string } } = {}
    for _, pet in ipairs(pets) do
        if type(pet) ~= "table" then continue end
        local record = pet :: { [string]: any }
        if text(record.uid) and text(record.species)
            and occurrences[record.uid] == 1 and record.variant == sourceVariant
            and record.protected == false and record.equipped == false and record.eligible == true then
            local group = groups[record.species]
            if not group then
                group = {}
                groups[record.species] = group
            end
            table.insert(group, record.uid)
        end
    end
    local species: { string } = {}
    for name, group in pairs(groups) do
        if #group >= 6 then table.insert(species, name) end
    end
    table.sort(species)
    if #species == 0 then
        return nil, "Six eligible, unprotected and unequipped pets of one species are required."
    end
    local chosen = groups[species[1]]
    table.sort(chosen)
    return { chosen[1], chosen[2], chosen[3], chosen[4], chosen[5], chosen[6] }, nil
end

return ConversionPolicy
