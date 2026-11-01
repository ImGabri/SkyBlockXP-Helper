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

function Jobs:blocked(name)
    local slot = self.slots[name]
    return slot ~= nil and slot.cancelled == true
end

function Jobs:summary()
    local names = {}
    for name in pairs(self.slots) do table.insert(names, name) end
    table.sort(names)
    if #names == 0 then return "No active jobs." end
    local lines, now = {}, self.driver.clock()
    for _, name in ipairs(names) do
        local slot = self.slots[name]
        local state = if slot.cancelled then "cancellation pending" else "running"
        table.insert(lines, string.format("%s: %s (%.1fs / %.1fs)",
            name, state, math.max(0, now - slot.started), slot.timeout))
    end
    return table.concat(lines, "\n")
end

function Jobs:start(name, timeout, work, complete)
    if self.slots[name] then return false end
    local slot = { started = self.driver.clock(), timeout = timeout, complete = complete, cancelled = false }
    self.slots[name] = slot
    slot.thread = self.driver.spawn(function()
        local function active()
            return self.slots[name] == slot and not slot.cancelled
        end
        if not active() then return end
        local outcome = table.pack(pcall(work, active))
        if self.slots[name] ~= slot then return end
        self.slots[name] = nil
        if slot.cancelled then return end
        complete(table.unpack(outcome, 1, outcome.n))
    end)
    return true
end

function Jobs:cancel(name)
    local slot = self.slots[name]
    if not slot then return end
    slot.cancelled = true
    -- Failed native cancellation cannot make an in-flight request disappear.
    -- Keep its slot reserved, and let the cooperative token block further calls.
    if slot.thread then
        local ok = pcall(self.driver.cancel, slot.thread)
        if ok and self.slots[name] == slot then self.slots[name] = nil end
    end
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
        if not slot.cancelled and now - slot.started >= slot.timeout then
            table.insert(expired, { name = name, slot = slot })
        end
    end
    for _, entry in ipairs(expired) do
        local name, slot = entry.name, entry.slot
        if self.slots[name] == slot and not slot.cancelled then
            self:cancel(name)
            local pending = self.slots[name] == slot
            slot.complete(false, if pending
                then "Request timed out. Native cancellation did not finish; retry blocked until worker exits."
                else "Request timed out; worker cancelled. No automatic retry was sent.")
        end
    end
end

return Jobs
