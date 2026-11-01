--!nocheck

local UserInputService = game:GetService("UserInputService")

local Interface = {}

local colors = {
    background = Color3.fromRGB(15, 23, 36),
    surface = Color3.fromRGB(24, 35, 51),
    border = Color3.fromRGB(43, 59, 78),
    accent = Color3.fromRGB(54, 210, 221),
    text = Color3.fromRGB(231, 239, 249),
    muted = Color3.fromRGB(152, 170, 192),
    danger = Color3.fromRGB(255, 132, 132),
}

local defaults = {
    AutoFarm = false,
    AutoCollectOrbs = false,
    AutoCollectLootbags = false,
    WalkToTarget = false,
    FarmMode = "Nearest",
    Area = "All",
    NameFilter = "",
    Radius = 250,
    FarmInterval = 1,
    MovementEnabled = false,
    Fullbright = false,
    AntiIdle = false,
    WalkSpeed = 16,
    JumpPower = 50,
}

local function make(className, properties, parent)
    local instance = Instance.new(className)
    for key, value in pairs(properties) do
        instance[key] = value
    end
    instance.Parent = parent
    return instance
end

local function corner(parent, radius)
    make("UICorner", { CornerRadius = UDim.new(0, radius or 8) }, parent)
end

local function label(parent, properties)
    local props = {
        BackgroundTransparency = 1,
        BorderSizePixel = 0,
        Font = Enum.Font.Gotham,
        TextSize = 13,
        TextColor3 = colors.text,
        TextXAlignment = Enum.TextXAlignment.Left,
        TextYAlignment = Enum.TextYAlignment.Center,
    }
    for key, value in pairs(properties) do
        props[key] = value
    end
    return make("TextLabel", props, parent)
end

function Interface.mount(spec)
    assert(spec.parent, "Interface.mount needs a GUI parent")
    local connections = {}
    local renderers = {}
    local options = table.clone(defaults)
    for key, value in pairs(spec.options or {}) do
        options[key] = value
    end
    local snapshot = {}
    local revision = 0
    local destroyed = false
    local collapsed = false
    local localMessage = nil
    local localMessageUntil = 0
    local pages = {}
    local tabButtons = {}
    local selectedTab = "Farm"
    local dragInput = nil
    local dragStart = nil
    local panelStart = nil

    local function connect(signal, callback)
        local connection = signal:Connect(callback)
        table.insert(connections, connection)
        return connection
    end

    local gui = make("ScreenGui", {
        Name = "PetSimAutomationUi",
        ResetOnSpawn = false,
        DisplayOrder = 40,
        ZIndexBehavior = Enum.ZIndexBehavior.Sibling,
    }, spec.parent)

    local panel = make("Frame", {
        Name = "Panel",
        AnchorPoint = Vector2.new(0.5, 0.5),
        Position = UDim2.fromScale(0.5, 0.5),
        Size = UDim2.fromScale(0.92, 0.82),
        BackgroundColor3 = colors.background,
        BorderSizePixel = 0,
        ClipsDescendants = true,
    }, gui)
    corner(panel, 12)
    make("UIStroke", { Color = colors.border, Thickness = 1 }, panel)
    local sizeConstraint = make("UISizeConstraint", {
        MaxSize = Vector2.new(520, 620),
        MinSize = Vector2.new(280, 280),
    }, panel)

    local header = make("Frame", {
        Name = "Header",
        Size = UDim2.new(1, 0, 0, 48),
        BackgroundColor3 = colors.surface,
        BorderSizePixel = 0,
        Active = true,
    }, panel)
    label(header, {
        Position = UDim2.fromOffset(14, 5),
        Size = UDim2.new(1, -108, 0, 21),
        Font = Enum.Font.GothamBold,
        TextSize = 14,
        Text = spec.name or "Pet Sim Automation",
        TextTruncate = Enum.TextTruncate.AtEnd,
    })
    label(header, {
        Position = UDim2.fromOffset(14, 26),
        Size = UDim2.new(1, -108, 0, 16),
        TextSize = 10,
        TextColor3 = colors.muted,
        Text = "v" .. tostring(spec.version or "0.0.0") .. "  /  Right Ctrl to hide",
    })

    local function headerButton(text, offset)
        local button = make("TextButton", {
            AnchorPoint = Vector2.new(1, 0.5),
            Position = UDim2.new(1, offset, 0.5, 0),
            Size = UDim2.fromOffset(30, 28),
            BackgroundColor3 = colors.background,
            BorderSizePixel = 0,
            Font = Enum.Font.GothamBold,
            TextSize = 17,
            TextColor3 = colors.muted,
            Text = text,
        }, header)
        corner(button, 6)
        return button
    end
    local collapseButton = headerButton("-", -46)
    local unloadButton = headerButton("x", -10)

    local body = make("Frame", {
        Position = UDim2.fromOffset(12, 58),
        Size = UDim2.new(1, -24, 1, -70),
        BackgroundTransparency = 1,
        BorderSizePixel = 0,
    }, panel)
    local tabBar = make("Frame", {
        Size = UDim2.new(1, 0, 0, 32),
        BackgroundTransparency = 1,
    }, body)
    make("UIListLayout", {
        FillDirection = Enum.FillDirection.Horizontal,
        Padding = UDim.new(0, 6),
        SortOrder = Enum.SortOrder.LayoutOrder,
    }, tabBar)

    local content = make("Frame", {
        Position = UDim2.fromOffset(0, 42),
        Size = UDim2.new(1, 0, 1, -99),
        BackgroundTransparency = 1,
        BorderSizePixel = 0,
    }, body)
    local statusLabel = label(body, {
        Position = UDim2.new(0, 0, 1, -50),
        Size = UDim2.new(1, 0, 0, 22),
        TextSize = 11,
        TextColor3 = colors.accent,
        Text = "Starting...",
        TextTruncate = Enum.TextTruncate.AtEnd,
    })
    local messageLabel = label(body, {
        Position = UDim2.new(0, 0, 1, -27),
        Size = UDim2.new(1, 0, 0, 27),
        TextSize = 10,
        TextColor3 = colors.muted,
        Text = "All automation starts disabled.",
        TextWrapped = true,
        TextYAlignment = Enum.TextYAlignment.Top,
    })

    local function supported(key)
        return not snapshot.Supported or snapshot.Supported[key] ~= false
    end

    local function showMessage(text)
        localMessage = tostring(text)
        localMessageUntil = os.clock() + 8
        messageLabel.Text = localMessage
        messageLabel.TextColor3 = colors.danger
    end

    local function refresh()
        if destroyed then
            return
        end
        for _, render in ipairs(renderers) do
            render()
        end
        statusLabel.Text = tostring(snapshot.Status or "Ready")
        local errorText = snapshot.LastError
        if localMessage and os.clock() < localMessageUntil then
            messageLabel.Text = localMessage
            messageLabel.TextColor3 = colors.danger
        elseif errorText and errorText ~= "" then
            messageLabel.Text = tostring(errorText)
            messageLabel.TextColor3 = colors.danger
        else
            messageLabel.Text = "Right Ctrl: show / hide  |  Stop all pauses automation"
            messageLabel.TextColor3 = colors.muted
        end
    end

    local function change(key, value)
        if destroyed or not supported(key) then
            return
        end
        local before = revision
        local called, accepted, reason = pcall(spec.onChange, key, value)
        if not called or accepted == false then
            showMessage(if called then reason or "Setting was rejected." else accepted)
            refresh()
            return
        end
        -- A synchronous canonical snapshot takes precedence over raw textbox input.
        if revision == before then options[key] = value end
        localMessage = nil
        refresh()
    end

    local function action(name)
        if destroyed then
            return
        end
        local called, accepted, reason = pcall(spec.onAction, name)
        if not called or accepted == false then
            showMessage(if called then reason or "Action could not finish." else accepted)
        end
    end

    for index, name in ipairs({ "Farm", "Misc", "Status" }) do
        local button = make("TextButton", {
            Name = name,
            Size = UDim2.new(1 / 3, -4, 1, 0),
            BackgroundColor3 = colors.surface,
            BorderSizePixel = 0,
            Font = Enum.Font.GothamMedium,
            TextSize = 12,
            Text = name,
            TextColor3 = colors.muted,
            LayoutOrder = index,
        }, tabBar)
        corner(button, 7)
        tabButtons[name] = button
        local page = make("ScrollingFrame", {
            Name = name,
            Size = UDim2.fromScale(1, 1),
            BackgroundTransparency = 1,
            BorderSizePixel = 0,
            ScrollBarThickness = 3,
            ScrollBarImageColor3 = colors.border,
            CanvasSize = UDim2.new(),
            AutomaticCanvasSize = Enum.AutomaticSize.Y,
            ScrollingDirection = Enum.ScrollingDirection.Y,
            Visible = name == selectedTab,
        }, content)
        make("UIListLayout", {
            Padding = UDim.new(0, 7),
            SortOrder = Enum.SortOrder.LayoutOrder,
        }, page)
        make("UIPadding", { PaddingRight = UDim.new(0, 6), PaddingBottom = UDim.new(0, 7) }, page)
        pages[name] = page
        connect(button.Activated, function()
            selectedTab = name
            refresh()
        end)
    end
    table.insert(renderers, function()
        for name, page in pairs(pages) do
            page.Visible = name == selectedTab
            tabButtons[name].BackgroundColor3 = if name == selectedTab then colors.accent else colors.surface
            tabButtons[name].TextColor3 = if name == selectedTab then colors.background else colors.muted
        end
    end)

    local rowOrder = 0
    local function row(page, caption)
        rowOrder += 1
        local frame = make("Frame", {
            Size = UDim2.new(1, 0, 0, 42),
            BackgroundColor3 = colors.surface,
            BorderSizePixel = 0,
            LayoutOrder = rowOrder,
        }, pages[page])
        corner(frame, 7)
        local title = label(frame, {
            Position = UDim2.fromOffset(11, 0),
            Size = UDim2.new(0.57, -15, 1, 0),
            TextSize = 11,
            Text = caption,
            TextWrapped = true,
        })
        return frame, title
    end

    local function toggle(page, caption, key)
        local frame, title = row(page, caption)
        local button = make("TextButton", {
            AnchorPoint = Vector2.new(1, 0.5),
            Position = UDim2.new(1, -10, 0.5, 0),
            Size = UDim2.new(0.35, 0, 0, 26),
            BorderSizePixel = 0,
            Font = Enum.Font.GothamBold,
            TextSize = 10,
            Text = "OFF",
        }, frame)
        corner(button, 6)
        connect(button.Activated, function()
            change(key, not options[key])
        end)
        table.insert(renderers, function()
            local enabled = supported(key)
            button.Active = enabled
            button.AutoButtonColor = enabled
            button.Text = if not enabled then "UNAVAILABLE" elseif options[key] then "ON" else "OFF"
            button.BackgroundColor3 = if enabled and options[key] then colors.accent else colors.background
            button.TextColor3 = if enabled and options[key] then colors.background else colors.muted
            title.TextColor3 = if enabled then colors.text else colors.muted
        end)
    end

    local function input(page, caption, key, minimum, maximum)
        local frame, title = row(page, caption)
        local box = make("TextBox", {
            AnchorPoint = Vector2.new(1, 0.5),
            Position = UDim2.new(1, -10, 0.5, 0),
            Size = UDim2.new(0.4, 0, 0, 27),
            BackgroundColor3 = colors.background,
            BorderSizePixel = 0,
            ClearTextOnFocus = false,
            Font = Enum.Font.Gotham,
            TextSize = 11,
            TextColor3 = colors.text,
            Text = tostring(options[key] or ""),
            PlaceholderText = if key == "NameFilter" then "Any name" else "",
            PlaceholderColor3 = colors.muted,
        }, frame)
        corner(box, 6)
        connect(box.FocusLost, function()
            if destroyed then
                return
            end
            local value = box.Text
            if minimum then
                value = tonumber(value)
                if not value or value ~= value or value < minimum or value > maximum then
                    showMessage(caption .. ": enter a number from " .. minimum .. " to " .. maximum .. ".")
                    box.Text = tostring(options[key])
                    return
                end
            end
            change(key, value)
        end)
        table.insert(renderers, function()
            local enabled = supported(key)
            box.TextEditable = enabled
            title.TextColor3 = if enabled then colors.text else colors.muted
            if not box:IsFocused() then
                box.Text = tostring(options[key] or "")
            end
        end)
    end

    local function cycle(page, caption, key, values)
        local frame = row(page, caption)
        local button = make("TextButton", {
            AnchorPoint = Vector2.new(1, 0.5),
            Position = UDim2.new(1, -10, 0.5, 0),
            Size = UDim2.new(0.4, 0, 0, 27),
            BackgroundColor3 = colors.background,
            BorderSizePixel = 0,
            Font = Enum.Font.GothamMedium,
            TextSize = 11,
            TextColor3 = colors.accent,
        }, frame)
        corner(button, 6)
        connect(button.Activated, function()
            local index = table.find(values, options[key]) or 0
            change(key, values[index % #values + 1])
        end)
        table.insert(renderers, function()
            button.Text = tostring(options[key]) .. " >"
            button.Active = supported(key)
        end)
    end

    local function actionButton(page, caption, name, danger)
        rowOrder += 1
        local button = make("TextButton", {
            Size = UDim2.new(1, 0, 0, 34),
            BackgroundColor3 = colors.surface,
            BorderSizePixel = 0,
            Font = Enum.Font.GothamMedium,
            TextSize = 11,
            Text = caption,
            TextColor3 = if danger then colors.danger else colors.accent,
            LayoutOrder = rowOrder,
        }, pages[page])
        corner(button, 7)
        connect(button.Activated, function()
            action(name)
        end)
    end

    toggle("Farm", "Auto farm", "AutoFarm")
    toggle("Farm", "Collect orbs", "AutoCollectOrbs")
    toggle("Farm", "Collect lootbags", "AutoCollectLootbags")
    toggle("Farm", "Walk toward target", "WalkToTarget")
    cycle("Farm", "Target priority", "FarmMode", { "Nearest", "Weakest", "Strongest" })
    input("Farm", "Area (All = any)", "Area")
    input("Farm", "Target name contains", "NameFilter")
    input("Farm", "Search radius (studs)", "Radius", 10, 1000)
    input("Farm", "Farm interval (seconds)", "FarmInterval", 0.25, 10)
    actionButton("Farm", "Run compatibility check", "Reconnect")
    actionButton("Farm", "STOP ALL", "StopAll", true)

    toggle("Misc", "Custom movement", "MovementEnabled")
    input("Misc", "Walk speed", "WalkSpeed", 8, 100)
    input("Misc", "Jump power", "JumpPower", 0, 150)
    actionButton("Misc", "Restore original movement", "ResetMovement")
    toggle("Misc", "Fullbright", "Fullbright")
    toggle("Misc", "Prevent idle disconnect", "AntiIdle")
    actionButton("Misc", "Rejoin current game", "Rejoin")

    rowOrder += 1
    local details = label(pages.Status, {
        Size = UDim2.new(1, -10, 0, 0),
        AutomaticSize = Enum.AutomaticSize.Y,
        TextSize = 12,
        TextWrapped = true,
        TextYAlignment = Enum.TextYAlignment.Top,
        LineHeight = 1.35,
        LayoutOrder = rowOrder,
    })
    table.insert(renderers, function()
        details.Text = string.format(
            "SESSION\n%s\n\nTarget: %s\nEquipped pets: %s\nFarm dispatches: %s\nOrb requests: %s\nLootbag requests: %s\n\nCAPABILITIES\n%s\n\nLAST ERROR\n%s",
            tostring(snapshot.Status or "Ready"),
            tostring(snapshot.Target or "None"),
            tostring(snapshot.EquippedPets or 0),
            tostring(snapshot.Farmed or 0),
            tostring(snapshot.CollectedOrbs or 0),
            tostring(snapshot.CollectedLootbags or 0),
            tostring(snapshot.Capabilities or "Checking..."),
            tostring(snapshot.LastError or "None")
        )
    end)
    actionButton("Status", "Copy diagnostics", "CopyDiagnostics")
    actionButton("Status", "Unload suite and restore settings", "Unload", true)

    connect(collapseButton.Activated, function()
        collapsed = not collapsed
        body.Visible = not collapsed
        panel.Size = if collapsed then UDim2.new(0.92, 0, 0, 48) else UDim2.fromScale(0.92, 0.82)
        sizeConstraint.MaxSize = if collapsed then Vector2.new(520, 48) else Vector2.new(520, 620)
        sizeConstraint.MinSize = if collapsed then Vector2.new(280, 48) else Vector2.new(280, 280)
        collapseButton.Text = if collapsed then "+" else "-"
    end)
    connect(unloadButton.Activated, function()
        action("Unload")
    end)
    connect(UserInputService.InputBegan, function(inputObject, processed)
        if not processed and not UserInputService:GetFocusedTextBox() and inputObject.KeyCode == Enum.KeyCode.RightControl then
            gui.Enabled = not gui.Enabled
        end
    end)
    connect(header.InputBegan, function(inputObject)
        if inputObject.UserInputType == Enum.UserInputType.MouseButton1 or inputObject.UserInputType == Enum.UserInputType.Touch then
            dragInput = inputObject
            dragStart = inputObject.Position
            panelStart = panel.Position
        end
    end)
    connect(UserInputService.InputChanged, function(inputObject)
        if not dragInput then
            return
        end
        local isMouse = dragInput.UserInputType == Enum.UserInputType.MouseButton1
            and inputObject.UserInputType == Enum.UserInputType.MouseMovement
        if isMouse or inputObject == dragInput then
            local delta = inputObject.Position - dragStart
            local parentSize = gui.AbsoluteSize
            local halfWidth = panel.AbsoluteSize.X / 2
            local halfHeight = panel.AbsoluteSize.Y / 2
            local x = panelStart.X.Scale * parentSize.X + panelStart.X.Offset + delta.X
            local y = panelStart.Y.Scale * parentSize.Y + panelStart.Y.Offset + delta.Y
            -- Keep a reachable header and prevent losing the panel off-screen.
            x = math.clamp(x, halfWidth, math.max(halfWidth, parentSize.X - halfWidth))
            y = math.clamp(y, halfHeight, math.max(halfHeight, parentSize.Y - halfHeight))
            panel.Position = UDim2.fromOffset(x, y)
        end
    end)
    connect(UserInputService.InputEnded, function(inputObject)
        if inputObject == dragInput then
            dragInput = nil
        end
    end)

    local handle = {}
    function handle:Update(nextSnapshot)
        if destroyed then
            return
        end
        snapshot = nextSnapshot or {}
        revision += 1
        for key, value in pairs(snapshot.Options or {}) do
            options[key] = value
        end
        refresh()
    end

    function handle:Destroy()
        if destroyed then
            return
        end
        destroyed = true
        dragInput = nil
        for _, connection in ipairs(connections) do
            connection:Disconnect()
        end
        table.clear(connections)
        gui:Destroy()
    end

    refresh()
    return handle
end

return Interface
