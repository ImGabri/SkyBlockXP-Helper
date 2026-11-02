# Pet Sim 99 (Pet Sim X) Automation suite

Version **0.8.0**, targeting the PSX Classic Event inside Pet Simulator99:
place `85920622393590`, universe `3317771874`.

This development build includes farming, pet tools, native-menu shortcuts and
local utilities. **Live event acceptance is unverified.** The user's earlier
coin route returned no values and logged a caller-script assertion. The public
Library/original-loader route and the new pet commands may still be rejected by
the current game. Passing local tests does not establish successful game actions.

## Run

The standalone script is [`dist/PetSim99AutomationSuite.lua`](dist/PetSim99AutomationSuite.lua).
Enter a fresh Classic Event client, then copy that file into Solara and execute,
or load the published main-branch build:

```lua
loadstring(game:HttpGet("https://raw.githubusercontent.com/ImGabri/SkyBlockXP-Helper/main/dist/PetSim99AutomationSuite.lua"))()
```

Confirm the title shows v0.8.0. Startup is passive and all automation starts off.
Right Control hides the panel; Stop All disables automation; Unload restores
local movement, lighting and menu states owned by the suite.

## Eggs, gold and rainbow

1. In **Pets**, click **Load pet tools**. This loads the public Library APIs
   independently of the coin compatibility check; it does not send a remote probe.
2. Use **Next egg** or enter the exact egg directory name. Choose Single, Triple
   or Octuple, then **Open egg once** before enabling Auto hatch. Multiple hatch
   modes require whatever access the server normally requires. Premium/Robux eggs
   are excluded. Auto hatch waits for enough currency, then resumes without
   switching itself off. The directory price is a conservative affordability
   check; current server discounts and costs remain authoritative. Leave **Egg
   travel → Walk** enabled to approach the unique loaded egg model before purchase.
   **Go to selected egg** walks without buying; **Off** leaves positioning to you.
3. Click **Open inventory** and let its pet slots load. Use **Next conversion
   species** or enter one exact species name/ID. An empty selection never converts.
4. Leave **Machine travel → Walk** enabled. The suite checks for an eligible batch,
   walks to the loaded machine Pad, verifies proximity and re-reads inventory before
   submitting. **Go to gold/rainbow machine** walks without spending pets. If the
   machine is in another unloaded world or no path exists, enter its unlocked area
   normally and retry. **Off** leaves travel to you.
5. **Convert6 to gold** uses six Normal pets; **Convert6 gold to rainbow** uses
   six Gold pets. Auto gold / Auto rainbow use the same fixed six-pet rule. Both
   stages can run with Auto hatch; inventory updates determine when another batch
   becomes available. Species and variants are never mixed.
6. Gold/rainbow menu buttons approach their machine first in Walk mode, then
   enable its existing ScreenGui. Egg/inventory buttons enable existing menus if
   present. A missing menu is reported; no menu, machine access or server permission
   is fabricated. The Egg menu name remains a runtime candidate.

Conversions require a loaded UID-named inventory button with an explicitly hidden
Locked indicator. Missing or locked slots are excluded. Equipped pets, duplicate
UIDs, premium/Exclusive/Event/Huge/Titanic pets, recognized protected variants,
nicknamed pets and pets with nonempty enchantments are excluded. Some raw optional
protection flags are defensive legacy checks; the current live inventory schema
is not verified. No pets are unlocked. The suite retains submitted UIDs while
inventory replication lags, including uncertain replies, to prevent replay.
An explicit false reply saying "too far" preserves the server message, stops the
operation and releases only that unconsumed batch for manual retry after moving.
Unknown replies retain their reservations; no automatic retry is sent.

Historical PSX examples label six pets as100%. This build enforces exactly six;
**the current server controls the actual chance, costs, access and range**. It
cannot promise100% or open eggs/use machines from every location. A request without
a true acknowledgement stops that feature. Request counters are not reward counts.

## Farm and other utilities

Farm → **Inspect local environment (no network)** checks the event destination, Library,
loaded coins and character root without requiring a module or sending remote
requests. It reports missing objects immediately; a pass does **not** prove
compatibility. **Run compatibility check** performs the separate native Get Coins
probe only if local preflight passes. The Status page now shows live probe/pet
stages and running or cancellation-pending workers. Request-timeout errors
distinguish successful cancellation from a worker that is still pending.
A rejected or hung native call is not retried automatically.

Farm → **Run compatibility check** makes one native Get Coins attempt. Only a
strictly valid reply matching loaded coin Models enables the experimental farm
and pickup controls. Start with Nearest priority. Empty/rejected replies stay
blocked; do not repeatedly probe a rejected route. Rejoin if a previous script
started repeating game-module warnings.

Farming accepts guarded legacy/current coin shapes (`health`/`h`, loaded
`Coin`/`POS` markers); invalid or conflicting health is rejected. Per-pet Join Coin
results must explicitly accept a UID before Farm Coin is sent.
Farming supports equipped-pet dispatch, radius/area/name filters, target priorities,
optional walking and nearby orb/lootbag requests. It does not establish map-wide
server access. Misc offers movement settings, Fullbright, optional idle input and
rejoin. Status shows diagnostics, separate pet/farm counters and Clear status error.

Machine walking uses ordinary Roblox pathfinding, with cancellation, jump
waypoints and a60-second travel deadline. Eight studs is a conservative local
arrival target, not an authoritative server-range guarantee. Missing/moved pads,
blocked paths and character replacement stop the trip before a conversion.
Egg walking uses the public WorldCmds.GetAllEggs list and an exact selected ID,
with a loaded Model and Center part. Missing or ambiguous models are reported;
enter the correct unlocked area normally or choose Off and approach manually.
Farm movement pauses during egg or machine journeys. Both travel modes recheck
target identity, current proximity and the current living rig through native
inventory reads immediately before submitting a request.

All pet mutations share one job slot; a pending uncancellable request cannot
be overlapped. Slow conversions cannot starve hatch/gold/rainbow stages. Pet mutations pause
while dead, preserve automatic options for respawn, and cannot continue on a
replaced root/humanoid. Stale cleanup cannot move a replacement rig. Disable,
timeout, respawn and Stop All cancel follow-up work. Native menus are local visual
shortcuts; closing/reopening does not bypass any game check.

Pet tools now report failed API loading in Last Error rather than silently
clearing the error whenever a loader returns normally. No network API failures
are disguised as successful game actions.

The script uses the original game loader `getrenv().require` when exposed,
otherwise ordinary require, through `ReplicatedStorage.Library`. Failed public
loading is not retried through private helpers. No hooks, guard changes, identity
spoofing, generic remote guessing or third-party loaders are used. Solara support
and current server command acceptance still need live testing.

## Build and check

```bash
bash scripts/setup-tools.sh
python3 scripts/build.py
bash scripts/check.sh
```

Pinned tools: Luau0.745 and Rojo7.7.1, downloaded with SHA256 verification. Python3
has no third-party dependencies. The checks run Python/Luau boundary and pure
logic tests, verify bundle freshness, compile all sources and build
`build/PetSim99AutomationSuite.rbxlx`. Roblox Studio can inspect local UI/utilities;
an empty Studio place cannot verify the event or executor.

Canonical product names are `PetSim99AutomationSuite` for the bundle, Studio
instance and session/UI identifiers. An old session marker is recognized to unload
older releases safely. Historical release documents retain their actual filenames.
The GitHub repository is public under its historical URL; an attempted repository
rename returned403 because the integration lacks administration access.

## Evidence and source layout

- `src/client/PetCare.luau`: public-library egg/machine commands and native menus.
- `src/client/ConversionPolicy.luau`: pure deterministic six-pet selection.
- `src/client/MachineNavigation.luau`: walking to loaded machine pads and selected egg Centers.
- `src/client/PetSim99.luau`: experimental coin adapter and diagnostics.
- `src/client/Runtime.luau`, `Jobs.luau`: scheduler, utilities, cancellation.
- `src/client/Interface.luau`, `Config.luau`, `Policy.luau`: UI and settings.
- `scripts/build.py`: standalone bundler; `tests/`: executable local fixtures.
- [`docs/research.md`](docs/research.md): pinned public references and limitations.
- [`v0.8.0 evidence`](docs/releases/0.8.0/ecc-tdd.md): actual RED/GREEN checkpoints.

[`dist/CopyClientConsole.lua`](dist/CopyClientConsole.lua) copies retained client
logs locally without loading game modules. Roblox may have expired older entries.
No credentials or inventory-transfer requests are collected by this suite.
