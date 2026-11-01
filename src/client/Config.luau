--!strict

return table.freeze({
    Name = "Pet Sim 99 (Pet Sim X) Automation suite",
    Version = "0.3.0",
    -- Observed in the user's Roblox client log while inside the Classic Event.
    Target = table.freeze({
        PlaceId = 85920622393590,
        UniverseId = 3317771874,
    }),
    Options = table.freeze({
        AutoFarm = false,
        AutoCollectOrbs = false,
        AutoCollectLootbags = false,
        WalkToTarget = false,
        FarmMode = "Nearest",
        Area = "All",
        NameFilter = "",
        Radius = 200,
        FarmInterval = 0.75,
        MovementEnabled = false,
        WalkSpeed = 24,
        JumpPower = 50,
        Fullbright = false,
        AntiIdle = false,
    }),
    RequestTimeout = 12,
    FarmTimeout = 60,
    RetryLimit = 3,
    ReassignSeconds = 10,
})
