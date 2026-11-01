# Pet Sim 99 (Pet Sim X) Automation suite

Development build targeting the **Classic Event inside Pet Simulator 99**.
This is not an adapter for the old standalone Pet Simulator X.

The user's in-event client log shows **place `85920622393590`**, universe
`3317771874`. Discovery now compares against that observed destination. This
identifies the reported event place, but does not establish its farming APIs.

**Version 0.5 changes module resolution; live compatibility still needs checking.**
The user's earlier screenshot shows `returns=0; types=none` from
Get Coins. Their client log contains repeated Network._check warnings mentioning
getgenv on Get Stats. The later log also contains a direct callerScript assertion
failure for Get Coins. The previous direct-client-module route supplied no usable
coin data in that session.

The new build uses the original game loader, `getrenv().require`, when the
executor provides it, and resolves Network/PetCmds through the public
`ReplicatedStorage.Library` module. This avoids explicitly loading the internal
client helpers. The selected loader/provider are included in diagnostics. If the
public entry fails, the build reports that failure without retrying the rejected
private route. This is a documented compatibility candidate, not evidence that
the game's caller validation now accepts it. No game check is modified.

Startup is now passive: loading the UI does not require game ModuleScripts or
send a coin probe. The compatibility check is an explicit action. A canceled
worker cannot issue follow-up requests, and a native request that cannot be
canceled keeps its slot occupied until it exits. This prevents overlapping
retries rather than pretending an in-flight request has disappeared.

**Requested feature status**

| Feature | Current evidence |
| --- | --- |
| UI/local movement/lighting controls | Implemented; UI loads in the user's client. |
| Experimental pet/nearby-pickup commands | Implemented; v0.5 public-library route is unverified in game. The older direct route failed. |
| Map-wide farming | No working current Classic Event backend verified. |
| Hatch from anywhere | Not implemented or verified. |
| Auto-gold / auto-rainbow | Not implemented or verified. |
| Executor-free input macro | Would require a visible recorded route; it cannot replace remote map-wide/hatching capabilities. |

After the network update, the rscripts.net index and official BIG Games posts
were accessed successfully. Relevant legacy sources and their limits are recorded
in docs/research.md. YouTube still returned HTTP403; no video was watched or
offered as compatibility proof.

The experimental adapter uses interface facts from a readable legacy PSX
reference. On a manual check, modules and coin replies must match strict,
loaded-model validation. Only a single coin dictionary or exactly
`(true, dictionary)` is accepted; false, empty, malformed and extra values block
the adapter. Diagnostics report count/types, not returned scalar contents.

## Implemented

- Pet auto-farm requests with all equipped pet UIDs, per-pet pacing, target
  reassignment throttling and no overlapping farming workers.
- Nearby orb/lootbag requests, bounded batches, a 30-stud maximum collection
  radius and per-object retry cooldowns.
- Optional walking toward a selected farm target; no automatic teleporting.
- Nearest/weakest/strongest priorities, area/radius/name filtering. Health-based
  modes require actual health data from the current response; use Nearest if absent.
- Cooperative cancellation on disable, timeout and respawn; no retry while an uncancellable request remains active.
- Original-loader/public-library resolution, including lazy proxies; canceled
  module lookups stop and stale work cannot overwrite a newer connection.
- Reentrant timeout callbacks cannot crash the scheduler or expire replacement jobs.
- Viewport/collapse resizing keeps Stop and Unload controls reachable.
- Self-contained executor script; native Roblox UI with Farm, Misc and Status
  tabs, mouse/touch dragging, collapse and Right Control to hide/show.
- Client movement settings with original-value restoration, including games
  that use JumpHeight instead of JumpPower.
- Fullbright with restoration, optional idle input, rejoin and rejoin errors.
- Stop All, unload cleanup and single-session replacement on repeated execution.
- Diagnostics showing observed IDs, visible game module names, protocol errors
  and request counters. Counters measure requests, not confirmed breaks/rewards.
- Timeout/cancellation job handling and a reproducible standalone bundler.

All toggles start off. The user confirmed the UI loads, but the previous coin
probe **failed**. The changed v0.5 farming/collection route has no live result yet. Movement changes may be
overridden by the game. Idle input and clipboard operations are optional and
report failure when rejected by the executor.

## Use the development build

The file to execute is **[`dist/PetSim99AutomationSuite.lua`](dist/PetSim99AutomationSuite.lua)**.

1. Enter the Classic Event, equip pets and stand beside loaded coins.
2. Rejoin first if an older build caused network-warning spam. Open the file,
   copy its complete contents into Solara and execute. Confirm the title shows v0.5.0.
3. The UI starts idle. Farm → **Run compatibility check** is a manual native-interface test, not a farming command. If it returns no values, stop retrying that route; use **Status → Copy diagnostics**.
4. Only after a successful probe, continue with the experimental controls.
5. In Farm, start with Nearest priority and enable Auto farm. Enable collection
   separately if desired. Right Control hides/shows the panel.
6. Use Stop All or Unload to stop requests and restore local movement/lighting.

Use the complete standalone file from `dist/`; the source modules do not need
to be downloaded separately.
It needs no remotely loaded UI library, hook/debug API, API key or file-writing
permission. It does not download or execute other scripts. It does require native
access to the game's public Library module; Solara may reject that access.
If `getrenv().require` is unavailable, ordinary `require` is used and reported;
if the selected loader fails, its error is surfaced rather than silently retried.

To help identify the event, open **Status → Copy diagnostics**. If clipboard
support is unavailable, the report is printed to the console. The report includes
object/module names and the compatibility error. It does not inspect inventory
contents or credentials. Send a failing report to diagnose the current adapter.
If a previous probe started repeating network warnings, rejoin a fresh client
before testing again. Unloading the UI does not own or stop game-module threads.
Do not keep probing a route that reports no values.

## Build and check

From the repository root on Linux x86_64:

```bash
bash scripts/setup-tools.sh
python3 scripts/build.py
bash scripts/check.sh
```

Setup requires Bash, curl, Python 3 and `sha256sum`. Official Luau 0.745 and
Rojo 7.7.1 archives are checked against pinned SHA-256 hashes. There are no Python
package dependencies. `check.sh` verifies bundle freshness, runs the Python and
Luau tests, compiles all sources and builds `build/PetSim99AutomationSuite.rbxlx`.

The generated `dist` script is kept with the sources. After editing Luau, rerun
`python3 scripts/build.py`; `--check` fails when the bundle is stale. The build
rewrites static local ModuleScript requires into lazy bundled modules. Game APIs
remain Roblox APIs; the standalone Luau CLI cannot emulate a real game.

## Roblox Studio

Open `build/PetSim99AutomationSuite.rbxlx` and select Play to inspect the UI and local
utilities. The client script and child modules are mapped under
`StarterPlayer > StarterPlayerScripts > PetSim99AutomationSuite` by Rojo. An empty
Studio place cannot validate the Classic Event's internals or Solara support.

## Source layout

- `src/client/init.client.luau`: client startup and single-session ownership.
- `src/client/Runtime.luau`: controls, local utilities and lifecycle cleanup.
- `src/client/Interface.luau`: native Roblox UI.
- `src/client/PetSim99.luau`: guarded legacy-protocol adapter and diagnostics.
- `src/client/Policy.luau`: pure targeting and settings rules.
- `src/client/Jobs.luau`: cancellation and timeout handling.
- `src/client/Config.luau`: defaults.
- `scripts/build.py`: deterministic executor bundle.
- `tests/`: bundler, adapter, actual-runtime/UI boundary, targeting and job-lifecycle checks.

Research and compatibility evidence: [`docs/research.md`](docs/research.md).

ECC test-first evidence: [`v0.5 module resolution`](docs/releases/0.5.0/ecc-tdd.md)
and [`v0.4 stability`](docs/releases/0.4.0/ecc-tdd.md).

To copy the retained client console without touching game modules, execute
[`dist/CopyClientConsole.lua`](dist/CopyClientConsole.lua). It copies locally;
Roblox may already have expired older log entries.
