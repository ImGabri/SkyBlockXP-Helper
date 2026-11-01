local Jobs = require("../src/client/Jobs")
local passed = 0
local function test(name, fn)
    fn()
    passed += 1
    print("PASS " .. name)
end
local function fixture()
    local now, queued, cancelled = 0, {}, {}
    local jobs = Jobs.new({
        clock = function() return now end,
        spawn = function(fn) table.insert(queued, fn); return fn end,
        cancel = function(thread) cancelled[thread] = true end,
    })
    return jobs, queued, cancelled, function(time) now = time end
end
test("a yielding feature cannot start overlapping requests", function()
    local jobs = fixture()
    assert(jobs:start("farm", 10, function() end, function() end))
    assert(not jobs:start("farm", 10, function() end, function() end))
end)
test("successful completion releases the feature slot", function()
    local jobs, queued = fixture()
    local value
    jobs:start("farm", 10, function() return 7 end, function(ok, result)
        assert(ok); value = result
    end)
    queued[1]()
    assert(value == 7 and not jobs:busy("farm"))
end)
test("worker errors reach the feature instead of killing the scheduler", function()
    local jobs, queued = fixture()
    local failure
    jobs:start("farm", 10, function() error("network unavailable") end, function(ok, message)
        assert(not ok); failure = message
    end)
    queued[1]()
    assert(string.find(failure, "network unavailable", 1, true))
    assert(not jobs:busy("farm"))
end)
test("timeout cancels the worker and reports once", function()
    local jobs, queued, cancelled, advance = fixture()
    local reports = 0
    jobs:start("farm", 10, function() return 1 end, function(ok)
        assert(not ok); reports += 1
    end)
    advance(10); jobs:tick(); jobs:tick()
    assert(cancelled[queued[1]] and reports == 1 and not jobs:busy("farm"))
    queued[1]() -- Even a late callback cannot publish a result after cancellation.
    assert(reports == 1)
end)
test("stale work cannot overwrite a newly started feature", function()
    local jobs, queued = fixture()
    local value = 0
    jobs:start("farm", 10, function() return 1 end, function(_, n) value = n end)
    jobs:cancel("farm")
    jobs:start("farm", 10, function() return 2 end, function(_, n) value = n end)
    queued[1]()
    assert(jobs:busy("farm") and value == 0)
    queued[2]()
    assert(not jobs:busy("farm") and value == 2)
end)
test("stop all cancels independent feature workers", function()
    local jobs, queued, cancelled = fixture()
    for _, key in ipairs({ "farm", "orbs", "lootbags" }) do
        jobs:start(key, 10, function() end, function() error("must not finish") end)
    end
    jobs:cancelAll()
    for _, fn in ipairs(queued) do assert(cancelled[fn]); fn() end
    assert(not jobs:busy("farm") and not jobs:busy("orbs") and not jobs:busy("lootbags"))
end)
print(string.format("%d tests passed", passed))
