# Pet Sim 99 (Pet Sim X) Automation suite

**v0.12.0**, for the PSX Classic Event in Pet Simulator 99:
place `85920622393590`, universe `3317771874`.

This release combines the latest B-key target farming from `ff56282` with the
pet-tool, walking and lifecycle changes developed in parallel. Both histories
are preserved. **The combined build has not been tested in a live Roblox client.**

The user's latest native diagnostics are failures, not successful backend proof:
Direct loads game modules, but Get Coins returns no values; local coin inspection
reported zero coin Models; Save.Get returned nil. The suite keeps native pet
mutations disabled when their required data is unavailable. Local input farming
is independent of those failed coin/save contracts.

## Execute

Join a fresh Classic Event client and execute
[`dist/PetSim99AutomationSuite.lua`](dist/PetSim99AutomationSuite.lua), or:

```lua
loadstring(game:HttpGet("https://raw.githubusercontent.com/ImGabri/SkyBlockXP-Helper/main/dist/PetSim99AutomationSuite.lua"))()
```

Confirm v0.12.0 in the title. Automatic actions start off. A local-only target
scan runs on load; it requires no game modules, Save.Get or remote requests.
Right Control hides/shows the panel. Stop All pauses automation; Unload restores
owned local movement, lighting and menu settings.

## Heaven Island detected-target farm

1. Stand in Heaven Island with equipped pets and verify that manually clicking
   a small breakable sends them to attack.
2. Face the small breakables. Press **B** or **START Heaven Island AutoFarm [B]**.
3. Hide the suite panel with **Right Control** and keep menus closed. The script
   requires positive Roblox focus, a clear native GUI hit test, a usable camera,
   `mousemoveabs`, `mouse1click` and `isrbxactive`. Missing checks pause input.
4. Press **B** again, STOP AutoFarm or STOP ALL to stop.

The scanner uses locally replicated names/tags for vaults, gifts, small chests,
coins and crates. It excludes known giant/Angel/Heaven's Gate chest names,
oversized models, pets and effects. It scans up to 40,000 descendants, refreshes
while running, and limits candidate distance to 160 studs. Objects need a visible
projection in the configured gameplay region. Aiming is followed by verification
that Mouse.Target belongs to the selected object; a mismatch never clicks.
Targets become eligible again after a cooldown of at least 3 seconds.

Mouse.Target verifies the world ray only. A separate guard checks actual cursor
coordinates, Roblox menu/text focus and PlayerGui objects before moving/clicking.
Visible or interactive GUI blocks input, including invisible-but-interactive
buttons inside transparent render groups. Unsupported or ambiguous native queries
pause input. These checks do not establish atomic OS input or identify every
possible protected CoreGui visual.

Input pauses during pet operations or travel, while dead, in a different game,
or without verified focus. A cached aim is discarded when interrupted. Typing
normally does not activate B. Scanning/aiming/clicking are not proof that pets
attacked, a breakable broke or rewards were collected. Unnamed, decorative or
unreplicated objects may not be identifiable; zero eligible targets means zero
clicks. The legacy cursor-chest helper remains only for compatibility.

Radius and Farm interval affect this input mode within its bounds. Priority,
Area, Name filter and Walk toward target belong to the legacy native adapter;
they do not tune the detected-target B farm.

## Pet tools: conditional on a valid game save

**The last reported Save.Get result was nil.** Until a fresh client exposes the
required public save data, native hatching/conversions remain unavailable.
Loading a ModuleScript does not establish a working inventory API.

1. Leave **Module path → Direct** selected, then click **Pets → Load pet tools**.
   This loads the known Network/Save/PetCmds/Directory child modules separately.
   **Inspect save layout** is read-only and reports types/return arity, not pet
   UIDs, balances or inventory contents. Nested unknown layouts are not guessed.
2. When a valid save exists, choose an exact egg using Next egg or its directory
   name. Single/Triple/Octuple require the server's normal access. Premium/Robux
   eggs are excluded. Auto hatch waits for sufficient currency instead of turning
   itself off; the directory price is conservative and may omit server discounts.
3. With **Egg travel → Walk**, the script resolves a unique loaded egg by its ID,
   walks to its Center and rechecks the target, proximity and funds before buying.
   Go to selected egg walks without buying. Off leaves positioning to you.
4. Open Inventory and load its pet slots. Select one exact conversion species.
   **Machine travel → Walk** checks eligibility, walks to the loaded Gold/Rainbow
   Pad, then rechecks inventory and proximity. Go-to-machine buttons spend no pets.
5. Gold uses exactly six Normal pets; Rainbow uses exactly six Gold pets of the
   same species. Equipped, duplicate, locked, premium/gift/Exclusive/Event/Huge/
   Titanic and recognized protected pets are excluded. Loaded UID-named inventory
   buttons with hidden lock indicators are required. Nicknamed/enchanted pets are
   excluded; optional legacy protection fields are not a verified current schema.

Six pets is the requested batch rule. **The server controls actual chances,
costs, range and access; 100% success is not promised.** Submitted UIDs remain
reserved while inventory replication lags. A definite false-plus-too-far reply
preserves the error and releases that unconsumed batch for manual retry. Unknown
or uncertain replies retain reservations; no automatic network retry is sent.

Walk modes use ordinary pathfinding with bounded deadlines and actual proximity
checks; no teleport, coordinates, range spoofing or machine unlocking. Missing,
moved, replaced or ambiguous targets stop the operation. Worlds must be entered
normally. Capture guards remain active through yielding native reads immediately
before submission. Dead/replaced rigs cannot spend pets; stale cleanup cannot
move a replacement rig. Pet actions share one worker slot and preserve canceled
requests until they exit when native cancellation is unavailable.

Native menu buttons enable existing Golden/Rainbow/Inventory ScreenGuis; machine
menus approach first in Walk mode. An Eggs menu is a candidate only and errors if
absent. A visible menu does not grant server access. Facade remains a manual
alternative after a fresh rejoin; there is no automatic fallback from a hung
loader. Optional original `getrenv().require` is used when exposed.

## Diagnostics and local utilities

Inspect local environment and Inspect visible coin models read local objects
without module loads or remote calls. The legacy Get Coins check stays explicitly
unsupported after the reported zero-value route and refuses an empty coin-model
area. Do not repeatedly probe a rejected route. Status shows stages, worker age,
input counters and actual errors; counters measure attempts, not rewards.

Movement settings, Fullbright, optional idle input, rejoin and Clear error remain
available. They restore owned settings on Stop All/Unload where applicable.
[`dist/CopyClientConsole.lua`](dist/CopyClientConsole.lua) copies retained client
logs locally; Roblox may already have expired older entries.

## Build and evidence

```bash
bash scripts/setup-tools.sh
python3 scripts/build.py
bash scripts/check.sh
```

Tools are pinned Luau 0.745 and Rojo 7.7.1 with SHA256 verification. The checks run
real source modules at explicit mocked Roblox boundaries, pure logic tests,
bundle freshness, compilation and Studio packaging. The Studio file is
`build/PetSim99AutomationSuite.rbxlx`; it cannot verify this event or Solara.

- [`docs/research.md`](docs/research.md): sources, shared-chat findings and limits.
- [`v0.12 evidence`](docs/releases/0.12.0/ecc-tdd.md): merge and RED/GREEN evidence.
- `src/client/Runtime.luau`: scheduling, input targeting and utilities.
- `PetCare.luau`, `ConversionPolicy.luau`: native pet commands and strict batches.
- `MachineNavigation.luau`, `ClickGuard.luau`: walking and input-state checks.
- `PetSim99.luau`: guarded legacy native adapter and local diagnostics.
- `scripts/build.py`: standalone bundle; `tests/`: executable boundary fixtures.

The provided paste/FlowAuth reference is an authenticated obfuscated launcher;
its hidden gameplay implementation was not copied or executed. No hooks, identity
changes, private remote extraction or third-party loader execution were added.
The GitHub repository is public under its historical URL; renaming previously
returned 403 because the integration lacks administration access.
