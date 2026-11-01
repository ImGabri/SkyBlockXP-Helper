--!nocheck
-- One worker per feature, cancellable on timeout, disable, reconnect and unload.
local Jobs = {}
Jobs.__index = Jobs

function Jobs.new(driver)
    return setmetatable({ slots = {}, driver = driver or {
        spawn = task.spawn, cancel = task.cancel, clock = os.clock,
    } }, Jobs)
end

function Jobs:busy(name)
    return self.slots[name] ~= nil
end

function Jobs:start(name, timeout, work, complete)
    if self.slots[name] then return false end
    local slot = { started = self.driver.clock(), timeout = timeout, complete = complete }
    self.slots[name] = slot
    slot.thread = self.driver.spawn(function()
        local outcome = table.pack(pcall(work))
        if self.slots[name] ~= slot then return end
        self.slots[name] = nil
        complete(table.unpack(outcome, 1, outcome.n))
    end)
    return true
end

function Jobs:cancel(name)
    local slot = self.slots[name]
    if not slot then return end
    self.slots[name] = nil
    if slot.thread then pcall(self.driver.cancel, slot.thread) end
end

function Jobs:cancelAll()
    local names = {}
    for name in pairs(self.slots) do table.insert(names, name) end
    for _, name in ipairs(names) do self:cancel(name) end
end

function Jobs:tick()
    local expired = {}
    local now = self.driver.clock()
    for name, slot in pairs(self.slots) do
        if now - slot.started >= slot.timeout then table.insert(expired, name) end
    end
    for _, name in ipairs(expired) do
        local slot = self.slots[name]
        self:cancel(name)
        slot.complete(false, "Request timed out; no overlapping retry was started.")
    end
end

return Jobs
