local Policy = require("../src/client/Policy")
local passed = 0
local function test(name, check)
    check()
    passed += 1
    print("PASS " .. name)
end
local function options(extra)
    local result = { Radius = 100, FarmMode = "Nearest", Area = "All", NameFilter = "" }
    for key, value in pairs(extra or {}) do result[key] = value end
    return result
end
local coins = {
    { id = "far", name = "Big Chest", area = "Forest", health = 500, distance = 90 },
    { id = "near", name = "Coin Pile", area = "Town", health = 40, distance = 10 },
    { id = "weak", name = "Small Chest", area = "Forest", health = 5, distance = 30 },
    { id = "dead", name = "Chest", area = "Town", health = 0, distance = 1 },
    { id = "outside", name = "Chest", area = "Town", health = 1, distance = 101 },
}
test("nearest ignores dead and out-of-range breakables", function()
    assert(Policy.select(coins, options()).id == "near")
end)
test("weakest uses health before distance", function()
    assert(Policy.select(coins, options({ FarmMode = "Weakest" })).id == "weak")
end)
test("strongest uses health before distance", function()
    assert(Policy.select(coins, options({ FarmMode = "Strongest" })).id == "far")
end)
test("area and chest filters are case-insensitive and combined", function()
    assert(Policy.select(coins, options({ Area = "FOREST", NameFilter = "chest" })).id == "weak")
end)
test("filter text is literal, not a Lua pattern", function()
    assert(Policy.select(coins, options({ NameFilter = "[" })) == nil)
end)
test("no matching breakables returns no target", function()
    assert(Policy.select(coins, options({ Area = "Missing" })) == nil)
end)
test("equal distance is deterministic", function()
    assert(Policy.select({
        { id = "z", name = "x", area = "x", health = 1, distance = 2 },
        { id = "a", name = "x", area = "x", health = 1, distance = 2 },
    }, options()).id == "a")
end)
test("numeric settings clamp to bounded values", function()
    assert(Policy.option("Radius", -5) == 10)
    assert(Policy.option("FarmInterval", 0) == 0.25)
    assert(Policy.option("WalkSpeed", "999") == 100)
end)
test("non-finite or invalid numbers are rejected", function()
    assert(Policy.option("Radius", 0/0) == nil)
    assert(Policy.option("Radius", math.huge) == nil)
    assert(Policy.option("Radius", "oops") == nil)
end)
test("invalid modes, booleans and unknown settings are rejected", function()
    assert(Policy.option("FarmMode", "Unknown") == nil)
    assert(Policy.option("AutoFarm", "true") == nil)
    assert(Policy.option("Unknown", true) == nil)
    assert(Policy.option("AutoFarm", false) == false)
end)
test("text is trimmed and empty area resets to All", function()
    assert(Policy.option("Area", "   ") == "All")
    assert(Policy.option("NameFilter", " chest ") == "chest")
end)
print(string.format("%d tests passed", passed))
