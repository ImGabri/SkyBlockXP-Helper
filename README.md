# Pet Sim 99 (Pet Sim X) Automation suite

Development build targeting the **Classic Event inside Pet Simulator 99**.
This is not an adapter for the old standalone Pet Simulator X.

The user's in-event client log shows **place `85920622393590`**, universe
`3317771874`. Discovery now compares against that observed destination. This
identifies the reported event place, but does not establish its farming APIs.

**Version 0.3 includes an experimental, guarded farming adapter.** The user's
in-game diagnostic matches a legacy PSX-style client layout: Library.Client
PetCmds/Network and __THINGS Coins/Orbs/Lootbags. Interface facts from a readable
legacy reference informed an original adapter; that is not proof of current
Classic Event or Solara compatibility.

On connection, native game modules must load and a Get Coins response must match
loaded coin models before farming controls become available. Unknown responses,
rejected calls or inaccessible modules leave/return the adapter to an unavailable
state. No hook, private-upvalue extraction or authentication bypass is included.

## Implemented

- Pet auto-farm requests with all equipped pet UIDs, per-pet pacing, target
  reassignment throttling and no overlapping farming workers.
- Nearby orb/lootbag requests, bounded batches, a 30-stud maximum collection
  radius and per-object retry cooldowns.
- Optional walking toward a selected farm target; no automatic teleporting.
- Nearest/weakest/strongest priorities, area/radius/name filtering. Health-based
  modes require actual health data from the current response; use Nearest if absent.
- Respawn cancellation, timeouts and explicit stop-on-protocol-failure behavior.
- Self-contained executor script; native Roblox UI with Farm, Misc and Status
  tabs, mouse/touch dragging, collapse and Right Control to hide/show.
- Client movement settings with original-value restoration, including games
  that use JumpHeight instead of JumpPower.
- Fullbright with restoration, optional idle input, rejoin and rejoin errors.
- Stop All, unload cleanup and single-session replacement on repeated execution.
- Diagnostics showing observed IDs, visible game module names, protocol errors
  and request counters. Counters measure requests, not confirmed breaks/rewards.
- Timeout/cancellation job handling and a reproducible standalone bundler.

All toggles start off. Solara compatibility and visual/in-game behavior have
**not** been verified in a running Roblox client. Movement changes may be
overridden by the game. Idle input and clipboard operations are optional and
report failure when rejected by the executor.

## Use the development build

The file to execute is **[`dist/PetSimAutomation.lua`](dist/PetSimAutomation.lua)**.

1. Enter the Classic Event, equip pets and stand beside loaded coins.
2. Open the file, copy its complete contents into Solara and execute.
3. Wait for **Protocol probe passed**. If unavailable, use **Status → Copy diagnostics**.
4. In Farm, start with Nearest priority and enable Auto farm. Enable collection
   separately if desired. Right Control hides/shows the panel.
5. Use Stop All or Unload to stop requests and restore local movement/lighting.

Use the complete standalone file from `dist/`; the source modules do not need
to be downloaded separately.
It needs no remotely loaded UI library, hook/debug API, API key or file-writing
permission. It does not download or execute other scripts. It does require native
access to the game's concrete client ModuleScripts; Solara may reject that access.

To help identify the event, open **Status → Copy diagnostics**. If clipboard
support is unavailable, the report is printed to the console. The report includes
object/module names and the compatibility error. It does not inspect inventory
contents or credentials. Send a failing report to diagnose the current adapter.
Use **Reconnect game adapter** after moving into the event to refresh discovery.

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
Luau tests, compiles all sources and builds `build/PetSimAutomation.rbxlx`.

The generated `dist` script is kept with the sources. After editing Luau, rerun
`python3 scripts/build.py`; `--check` fails when the bundle is stale. The build
rewrites static local ModuleScript requires into lazy bundled modules. Game APIs
remain Roblox APIs; the standalone Luau CLI cannot emulate a real game.

## Roblox Studio

Open `build/PetSimAutomation.rbxlx` and select Play to inspect the UI and local
utilities. The client script and child modules are mapped under
`StarterPlayer > StarterPlayerScripts > PetSimAutomation` by Rojo. An empty
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
- `tests/`: bundler, targeting and job-lifecycle checks.

Research and compatibility evidence: [`docs/research.md`](docs/research.md).
