--!nocheck
-- Read native focus/cursor/GUI state immediately before injecting input.
-- This helper never moves the mouse, clicks, loads game modules or caches a pass.
local ClickGuard = {}

local function finite(value)
    return type(value) == "number" and value == value and math.abs(value) < math.huge
end

local function alpha(value)
    return finite(value) and value >= 0 and value <= 1
end

local function call(object, name, ...)
    local method = object and object[name]
    if type(method) ~= "function" then return false end
    return pcall(method, object, ...)
end

-- Empty chains are hidden. Nil plus a reason means the native data is ambiguous.
local function visibleChain(hit, playerGui)
    if typeof(hit) ~= "Instance" or not hit:IsA("GuiObject") then
        return nil, "GUI hit query returned an unknown object."
    end
    local chain, node = {}, hit
    for _ = 1, 64 do
        if node == playerGui then return chain end
        if typeof(node) ~= "Instance" then return nil, "GUI ancestry could not be verified." end
        if node:IsA("GuiObject") then
            if type(node.Visible) ~= "boolean" then return nil, "GUI visibility is unreadable." end
            if not node.Visible then return {} end
            if node:IsA("CanvasGroup") then
                if not alpha(node.GroupTransparency) then return nil, "GUI group visibility is unreadable." end
                if node.GroupTransparency == 1 then return {} end
            end
            table.insert(chain, node)
        elseif node:IsA("LayerCollector") then
            if type(node.Enabled) ~= "boolean" then return nil, "GUI enabled state is unreadable." end
            if not node.Enabled then return {} end
        end
        node = node.Parent
    end
    return nil, "GUI ancestry exceeded the verification limit."
end

local function obstructs(node)
    if node:IsA("GuiButton") or node:IsA("TextBox") then return true end
    if type(node.Active) ~= "boolean" then return nil, "GUI interactivity is unreadable." end
    if node.Active then return true end
    if not alpha(node.BackgroundTransparency) then return nil, "GUI opacity is unreadable." end
    if node.BackgroundTransparency < 1 then return true end
    if node:IsA("ImageLabel") then
        if not alpha(node.ImageTransparency) then return nil, "GUI image opacity is unreadable." end
        if node.ImageTransparency < 1 then
            if type(node.Image) ~= "string" then return nil, "GUI image content is unreadable." end
            if node.Image ~= "" then return true end
        end
    end
    if node:IsA("TextLabel") then
        if not alpha(node.TextTransparency) or not alpha(node.TextStrokeTransparency) then
            return nil, "GUI text opacity is unreadable."
        end
        if node.TextTransparency < 1 or node.TextStrokeTransparency < 1 then
            if type(node.Text) ~= "string" then return nil, "GUI text content is unreadable." end
            if node.Text ~= "" then return true end
        end
    end
    return false
end

local function check(player, input, guiService, isActive)
    if type(isActive) ~= "function" then return false, "Roblox focus verification is unavailable (isrbxactive)." end
    local focusOk, active = pcall(isActive)
    if not focusOk or active ~= true then return false, "Paused: Roblox focus is not verified." end
    local textOk, textBox = call(input, "GetFocusedTextBox")
    if not textOk then return false, "Focused text input could not be checked." end
    if textBox ~= nil then return false, "Paused: a text box has focus." end
    local menu = guiService and guiService.MenuIsOpen
    if type(menu) ~= "boolean" then return false, "Roblox menu state could not be checked." end
    if menu then return false, "Paused: the Roblox menu is open." end
    local cursorOk, cursor = call(input, "GetMouseLocation")
    if not cursorOk or not cursor or not finite(cursor.X) or not finite(cursor.Y) then
        return false, "Actual mouse position could not be checked."
    end
    local guiOk, playerGui = call(player, "FindFirstChild", "PlayerGui")
    if not guiOk or typeof(playerGui) ~= "Instance" or not playerGui:IsA("PlayerGui") then
        return false, "PlayerGui is unavailable for native hit testing."
    end
    local hitsOk, hits = call(playerGui, "GetGuiObjectsAtPosition", cursor.X, cursor.Y)
    if not hitsOk or type(hits) ~= "table" then return false, "Native GUI hit testing is unavailable." end
    local size = #hits
    for key in pairs(hits) do
        if type(key) ~= "number" or key < 1 or key % 1 ~= 0 or key > size then
            return false, "Native GUI hit query returned an unsupported list."
        end
    end
    for index = 1, size do
        local chain, reason = visibleChain(hits[index], playerGui)
        if not chain then return false, reason end
        for _, node in ipairs(chain) do
            local covered, issue = obstructs(node)
            if issue then return false, issue end
            if covered then return false, "Paused: visible or interactive GUI covers the cursor." end
        end
    end
    return true, nil
end

function ClickGuard.Check(player, input, guiService, isActive)
    local ok, allowed, reason = pcall(check, player, input, guiService, isActive)
    if not ok then return false, "Native input state could not be verified; no click sent." end
    return allowed, reason
end

return ClickGuard
