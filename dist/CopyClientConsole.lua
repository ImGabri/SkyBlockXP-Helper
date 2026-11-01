-- Copies the retained client log locally. No game modules or network calls.
local history = game:GetService("LogService"):GetLogHistory()
local lines = {}

for _, entry in ipairs(history) do
    table.insert(lines, string.format("[%s] %s", tostring(entry.messageType), tostring(entry.message)))
end

local copy = setclipboard or toclipboard
assert(type(copy) == "function", "Clipboard is unavailable in this executor.")
local ok, failure = pcall(copy, table.concat(lines, "\n"))
assert(ok, "Could not copy the client log: " .. tostring(failure))
print("Copied " .. #history .. " retained client console messages. Older messages may have expired.")
