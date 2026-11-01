local loaded, module = pcall(require, "../src/client/ConversionPolicy")
local passed, failed = 0, 0
local function batch(pets, target)
    assert(loaded and type(module) == "table" and type(module.NextBatch) == "function",
        "ConversionPolicy.NextBatch is not implemented")
    return module.NextBatch(pets, target)
end
local function test(name, check)
    local ok, message = pcall(check)
    if ok then
        passed += 1
        print("PASS " .. name)
    else
        failed += 1
        print("FAIL " .. name .. ": " .. tostring(message))
    end
end
local function pet(uid, species, variant, extra)
    local record = {
        uid = uid, species = species or "Cat", variant = variant or "Normal",
        protected = false, equipped = false, eligible = true,
    }
    for key, value in pairs(extra or {}) do record[key] = value end
    return record
end
local function six(species, variant)
    local result = {}
    for index = 1, 6 do
        table.insert(result, pet("pet-" .. tostring(index), species, variant))
    end
    return result
end
local function denied(pets, target)
    local ids, reason = batch(pets, target)
    assert(ids == nil, "ineligible inventory produced a conversion batch")
    assert(type(reason) == "string" and reason ~= "", "denial did not explain its reason")
end
local function equal(actual, expected)
    assert(type(actual) == "table" and #actual == #expected, "unexpected batch size")
    for index, uid in ipairs(expected) do assert(actual[index] == uid, "unexpected UID/order") end
end

test("gold selects exactly six normal pets of one species", function()
    equal(batch(six(), "Gold"), { "pet-1", "pet-2", "pet-3", "pet-4", "pet-5", "pet-6" })
end)
test("rainbow selects exactly six gold pets", function()
    equal(batch(six("Cat", "Gold"), "Rainbow"), { "pet-1", "pet-2", "pet-3", "pet-4", "pet-5", "pet-6" })
end)
test("five eligible pets never start a conversion", function()
    local pets = six()
    table.remove(pets)
    denied(pets, "Gold")
end)
test("seven eligible pets still submit only six deterministic UIDs", function()
    local pets = six()
    table.insert(pets, 1, pet("pet-0"))
    equal(batch(pets, "Gold"), { "pet-0", "pet-1", "pet-2", "pet-3", "pet-4", "pet-5" })
end)
test("normal gold and rainbow variants cannot be mixed", function()
    local pets = { pet("n1"), pet("n2"), pet("g1", "Cat", "Gold"), pet("g2", "Cat", "Gold"),
        pet("r1", "Cat", "Rainbow"), pet("r2", "Cat", "Rainbow") }
    denied(pets, "Gold")
    denied(pets, "Rainbow")
    denied(six("Cat", "Rainbow"), "Gold")
    denied(six("Cat", "Rainbow"), "Rainbow")
end)
test("different species never fill one six-pet batch", function()
    local pets = six()
    for index = 4, 6 do pets[index].species = "Dog" end
    denied(pets, "Gold")
end)
test("protected equipped and explicitly ineligible pets are excluded", function()
    for _, field in ipairs({ "protected", "equipped", "eligible" }) do
        local pets = six()
        pets[1][field] = field ~= "eligible"
        denied(pets, "Gold")
    end
end)
test("unknown eligibility and protection flags are excluded", function()
    for _, field in ipairs({ "protected", "equipped", "eligible" }) do
        local pets = six()
        pets[1][field] = nil
        denied(pets, "Gold")
        pets[1][field] = if field == "eligible" then 1 else 0
        denied(pets, "Gold")
    end
end)
test("duplicated UID is excluded even if its other record is protected", function()
    local pets = six()
    table.insert(pets, pet("pet-1", "Dog", "Gold", { protected = true }))
    denied(pets, "Gold")
end)
test("a duplicate UID never prevents selecting six other unique pets", function()
    local pets = six()
    table.insert(pets, pet("pet-1"))
    table.insert(pets, pet("pet-7"))
    equal(batch(pets, "Gold"), { "pet-2", "pet-3", "pet-4", "pet-5", "pet-6", "pet-7" })
end)
test("empty malformed or non-string identifiers cannot be converted", function()
    for _, change in ipairs({
        function(p) p.uid = "" end,
        function(p) p.uid = "   " end,
        function(p) p.uid = 1 end,
        function(p) p.species = "" end,
        function(p) p.species = false end,
        function(p) p.variant = "Unknown" end,
    }) do
        local pets = six()
        change(pets[1])
        denied(pets, "Gold")
    end
end)
test("input order does not change the chosen species or UIDs", function()
    local pets = six("Dog")
    local cats = six("Cat")
    for index, record in ipairs(cats) do
        record.uid = "cat-" .. tostring(index)
        table.insert(pets, 1, record)
    end
    equal(batch(pets, "Gold"), { "cat-1", "cat-2", "cat-3", "cat-4", "cat-5", "cat-6" })
    local reversed = {}
    for index = #pets, 1, -1 do table.insert(reversed, pets[index]) end
    equal(batch(reversed, "Gold"), { "cat-1", "cat-2", "cat-3", "cat-4", "cat-5", "cat-6" })
end)
test("the returned batch and selection leave caller inventory unchanged", function()
    local pets = six()
    local ids = batch(pets, "Gold")
    ids[1] = "changed"
    assert(pets[1].uid == "pet-1" and #pets == 6)
    assert(pets[1].variant == "Normal" and pets[1].eligible == true)
end)
test("empty inventory and unknown target variants are denied", function()
    denied({}, "Gold")
    denied(six(), "Normal")
    denied(six(), "gold")
    denied(six(), nil)
end)
test("malformed inventory containers are denied without throwing", function()
    denied(nil, "Gold")
    denied("pets", "Gold")
    denied({ extra = pet("x") }, "Gold")
    local pets = six()
    pets.extra = pet("extra")
    denied(pets, "Gold")
end)
test("malformed records do not make a valid group", function()
    local pets = six()
    pets[1] = false
    denied(pets, "Gold")
end)

print(string.format("%d tests passed, %d failed", passed, failed))
assert(failed == 0, "Conversion policy regression failures")
