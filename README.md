# Pet Sim 99 (Pet Sim X) Automation suite

Version **0.12.0**, targeting the PSX Classic Event inside Pet Simulator99:
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

Confirm the title shows v0.12.0. Startup is passive and all automation starts off.
Right Control hides the panel; Stop All disables automation; Unload restores
local movement, lighting and menu states owned by the suite.

## When the public Library facade hangs

If the diagnostic report stops at `Loading ReplicatedStorage.Library ModuleScript`,
the place may still be correct. Do **not** increase the timeout or repeatedly
run the hanging native call. Rejoin the Classic Event in a fresh client, then
use the default **Farm → Module path → Direct** for any manual compatibility check.
For pet tools choose Direct the same way before clicking **Load pet tools**.
Direct mode tries the existing `Library.Client.Network`,
`Library.Client.PetCmds`, `Library.Client.Save`, and `Library.Directory`
ModuleScripts individually and reports the exact module that stalls.
It does not fall back automatically from a hung facade or guess remotes.
Neither module access method is guaranteed to work in the live client.
The original **Facade** path remains available for reproducibility. To
switch modes after a successful load, rejoin first.

## v0.7.3: proven module loading, unsupported legacy Get Coins response

Live user diagnostics now confirm that Direct mode loads Network and PetCmds
successfully, but Network.Invoke("Get Coins") returns zero values. An earlier
in-game console showed a caller-script assertion for this legacy command.
There is no verified game contract for obtaining a coin dictionary through the
current event. **The suite does not fabricate a response or send repeated guesses
to unnamed RemoteEvents.** AutoFarm stays disabled after the failed compatibility
check. The Farm tab now includes **Inspect visible coin models (no network)**:
it reports locally loaded model/position-marker counts and up to 12 examples,
without requiring modules or contacting the server. This is diagnostic only,
not a replacement coin protocol.

Pet tools are **independent of Get Coins**. With Direct selected, try **Pets →
Load pet tools** separately and copy diagnostics; supported API loading,
hatching, and conversions must each be validated in-game before trusting them.

## v0.7.4: missing inventory save diagnostics

The client's confirmed Direct-module load passes, but the native `Get Coins`
call returns no data and the inspected `__THINGS.Coins` folder held zero models.
This is not evidence of a working farm protocol; AutoFarm stays blocked. Move
normally to an event coin area and inspect again without repeating the rejected
network probe.

Pet tools do load, but a live AutoGold attempt stopped before mutation because
`Save.Get()` did not provide a `Pets` table. Use **Pets → Inspect save layout
(read-only)** after **Load pet tools**. It calls `Save.Get` once and reports only
top-level types (`Pets`, `Inventory`, `Data`, `Save`) and the type of
nested `Pets` fields when present. It does **not** print inventory, UIDs,
balances or pet records; it does not send any game mutation request. This
diagnostic does not assume that nested data is safe for conversion. Conversion
will remain unavailable until the actual save contract can be validated.

## v0.7.5: exact nil-save result and preflight gating

The confirmed v0.7.4 live result showed `Save.Get` returning nil, rather
than an inventory table or an unexpected table shape. The **Inspect save layout**
button now reports the number and types of return values and callable argument
metadata (without dumping inventory details). A nil or invalid save automatically
disables pet conversion buttons for the session; a missing save table also
disables hatching because the currency balance cannot be verified. Reload pet
tools in a fresh session after the game save becomes available. This is a
defensive readiness check, not a server workaround.

**Run compatibility check** now refuses to invoke the already-failing
`Get Coins` command when no coin Models are present in the local `__THINGS.Coins`
folder. It does not interpret non-model children as coins. Debug listings
combine repeated names (e.g., identical RemoteEvent entries) to make reports
shorter. The previously seen `Get Coins` zero-value response remains
unsupported and will not be guessed or replaced with unverified data.

## v0.8.0: Heaven Island chest cursor assist

The current PSX Classic Event does not return a coin dictionary from the legacy
`Get Coins` call, and the user's Heaven Island local coin-model inspection was
empty. This version adds a separate **Arm Heaven chest: aim within 3 seconds**
button under Farm. It works independently of the blocked legacy AutoFarm and
never loads pet tools, calls Save.Get or sends network remotes.

1. Stand in Heaven Island, equip pets normally, and verify clicking the chest
   manually sends them to attack.
2. Scroll down inside Farm. The **HEAVEN: Aim at chest, arm within 3 seconds** button is near the bottom, directly above **Stop Heaven chest assist** and **STOP ALL**. The earlier **Legacy Get Coins check (NOT Heaven assist)** is a separate unsupported experimental probe. Click **Arm Heaven chest**. Within 3 seconds move the mouse cursor to the
   actual chest (not a GUI overlay), and leave the camera/cursor stationary.
3. The suite sends one `mouse1click()` input at that position. It waits until
   the targeted part leaves the Workspace, then clicks one matching replacement
   within 12 studs of the original part. This avoids click-spamming pets off
   a still-live chest.
4. **Stop Heaven chest assist** or **STOP ALL** immediately disables it. Closing
   Roblox or switching areas also requires re-arming.

This is a limited cursor assist **not verified automatic farming**:
the input function must be supported by the executor, the chest must expose a
clickable BasePart, and chest destruction must actually replace/remove it.
If the chest reuses the same instance or clicking doesn't select it, the helper
will not auto-retarget. It does not farm every breakable on Heaven Island or
confirm any reward. It does not bypass game limits.

## v0.11.0: B toggle, cursor verification and ongoing target retries

On startup, the suite performs a *local-only*, passive scan of replicated
Workspace objects. It looks for nearby individually named or tagged **vaults,
safes, gifts, presents, small chests, coins, coin piles and crates**, including
models in `__THINGS.Coins` if that folder is populated. This does **not**
load any game modules, invoke game remotes or use Save.Get. The target count
and category breakdown appear on Status; click **SCAN small breakables NOW**
to refresh on demand. A running farm refreshes the scan every seven seconds.

In Heaven Island (not Heaven's Gate), equip pets, close the Teleport menu,
face the small breakables, then press **B** (or click **START Heaven Island
AutoFarm [B]**). Press **B** again to stop. Typing into a text box will not
activate the hotkey. The script only moves the cursor to a candidate with a visible
world-to-screen position in the left gameplay view and clicks only when `Player:GetMouse().Target` confirms that the cursor
actually points to the selected world object. It retries each object on a
bounded cooldown instead of permanently excluding the same instance. Cursor
mismatches are counted in Status and never produce clicks. The current
input mode needs Roblox to be focused and both mouse input functions to
work; it never clicks a fixed screen pattern. Objects containing
known giant/Angel/Heaven's Gate chest names, large models, pets and effects
are excluded. **B**, **STOP Heaven Island AutoFarm**, or **STOP ALL** disables it.

This is a best-effort input-only targeting system, **not proven game-side
farming**. Generic/unreplicated breakables or decorative objects with
breakable-like names cannot reliably be distinguished from actual clickable
breakables without a verified game API. The scanner intentionally makes
**zero clicks** if it detects no eligible named/tagged targets, rather than
guessing coordinates. A detected object or input click does not confirm
pets attacked it or rewards were collected. The executor must support both
`mousemoveabs` and `mouse1click`; the failing Get Coins command and pet
tools are not required.

## Eggs, gold and rainbow## Eggs, gold and rainbow

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
