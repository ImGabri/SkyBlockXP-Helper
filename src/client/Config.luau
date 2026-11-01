--!strict

return table.freeze({
    Name = "Pet Sim 99 (Pet Sim X) Automation suite",
    Version = "0.10.0",
    -- Observed in the user's Roblox client log while inside the Classic Event.
    Target = table.freeze({
        PlaceId = 85920622393590,
        UniverseId = 3317771874,
    }),
    Options = table.freeze({
        AutoFarm = false,
        HeavenChestAssist = false, -- Previous single-chest assist; kept for compatibility.
        HeavenIslandSweep = false, -- Object-targeted local scanner; no module/network probing.
        AutoCollectOrbs = false,
        AutoCollectLootbags = false,
        WalkToTarget = false,
        FarmMode = "Nearest",
        ModulePathMode = "Direct", -- Live client loaded child modules; Facade remains a manual alternative.
        Area = "All",
        NameFilter = "",
        Radius = 200,
        FarmInterval = 0.75,
        AutoHatch = false,
        AutoGold = false,
        AutoRainbow = false,
        EggName = "",
        HatchMode = "Single",
        HatchInterval = 3,
        ConversionSpecies = "",
        ConversionInterval = 3,
        MachineTravelMode = "Walk",
        MovementEnabled = false,
        WalkSpeed = 24,
        JumpPower = 50,
        Fullbright = false,
        AntiIdle = false,
    }),
    RequestTimeout = 30,
    TravelTimeout = 60,
    FarmTimeout = 60,
    RetryLimit = 3,
    ReassignSeconds = 10,
})
