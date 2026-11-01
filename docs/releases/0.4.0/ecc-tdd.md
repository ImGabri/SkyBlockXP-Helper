# v0.4.0 — ECC test-first stability work

The source plan was derived from the user's failed native probe, repeated
client network warnings, requested feature parity and independent ECC reviews.
This is a stability/diagnostic release, not a verified working Classic Event bot.

## Journeys and evidence

| User-visible guarantee | RED evidence | GREEN evidence | Tests |
| --- | --- | --- | --- |
| Loading the UI does not automatically load game modules or call Get Coins | Runtime startup test invoked Connect immediately | Passive constructor, manual compatibility action | tests/test_runtime.py |
| Timed-out/disabled work cannot resume and send another farm or pickup request | Native cancellation failure freed its slot; old Join resumed and fired more requests | Occupied canceled slot plus cooperative work token, including across toggle reenables | tests/jobs.luau, tests/test_adapter.py, tests/test_runtime.py |
| Timeout callbacks may cancel/replace sibling jobs without crashing or expiring replacements | Nil complete access and incorrect replacement timeout | Expired entries capture slot identity and re-check before completion | tests/jobs.luau |
| Unexpected extra coin-response values do not unlock farming | Dictionary plus false/string unlocked controls | Exact single dictionary or exact true+dictionary only | tests/test_adapter.py |
| Canceled module loads stop before loading another game module | Canceled Network load still required PetCmds | Active-token barrier between module loads | tests/test_adapter.py |
| Errors from canceled native operations do not invalidate the live connection | Late canceled Join/Claim Orbs error disabled all capabilities | Active-token checks before propagating errors | tests/test_adapter.py |
| Scheduler errors are contained; movement/lighting restore on Stop All | Jobs.tick error escaped Pulse | Entire tick/step cycle protected, canonical stop state restored | tests/test_runtime.py |
| Stop/Unload remain reachable after viewport and panel resizing | Dragged controls remained outside smaller viewport | Both viewport/panel size handlers re-clamp and disconnect on unload | tests/test_interface.py |

## Checkpoint commits

- `db9a237` RED: job timeout and adapter cancellation/arity reproductions.
- `8d1d44b` GREEN: scheduler slot identity, cooperative tokens and strict arity.
- `60b4944` RED: passive startup and actual runtime cancellation reproductions.
- `29976c9` GREEN: runtime token wiring and explicit manual native probing.
- `560ab04` RED: viewport/panel resize reproductions against actual UI source.
- `256e020` GREEN: reachable controls and resize cleanup.
- `669ce69` RED: canceled module load and late native error reproductions.
- `e397289` GREEN: cancellation barriers and late-error isolation.

Checkpoint history remains on the current branch; it was not squashed.

## Commands and measured coverage

- `python3 -m unittest discover -s tests -p 'test_*.py' -v`
- `.tools/bin/luau tests/jobs.luau`
- `.tools/bin/luau tests/policy.luau`
- `.tools/bin/luau-analyze src/client/Config.luau src/client/Policy.luau`
- `bash scripts/check.sh` verifies bundle freshness, tests, compilation and Rojo build.
- Luau `--coverage` on the actual Jobs/Policy modules measured 45/48 executable
  lines (93.8%) for Jobs and 51/53 (96.2%) for Policy. This is executable-line
  coverage of those two pure modules, not coverage of all client code or a live
  gameplay run. Branch coverage and full Roblox-client coverage were not measured.

No formatter/linter is configured. Bash syntax, pure-module typing and Git
whitespace checks are separate evidence, not a substitute for full client typing.

## Target acceptance and remaining work

The user's actual v0.3.1 target check is FAILED: Get Coins returns zero values.
The later client log includes one direct `callerScript ... assertion failed`
warning for Get Coins at Client.Network:306 and 511 repeated getgenv/Get Stats
warnings through Network._check and Save.FetchPlayer. This is a caller-validation
failure, not proof of an alternative payload schema. The raw private log was
not committed.

No current backend for map-wide farming, remote hatching, auto-gold or
rainbow conversion has been validated. Historical command names and advertised
menus do not establish current permission or success. v0.4.0 has not been run
inside the user's Roblox client; local fixture success does not change that.

## Final local verification

`bash scripts/check.sh`:57 Python test methods +11 targeting +8 job tests =
**76 passed,0 skipped**. Nine source/bundle/helper files compile; Rojo build and
exact packaged-source comparison pass. Strict Config/Policy type checks, Bash
syntax, Git whitespace and a limited credential-pattern scan pass. No full
client type/branch-coverage or real Roblox gameplay acceptance is claimed.

The network update also enabled direct review of official BIG Games Update99
and100 and the user's rscripts index. Old source now documents the requested
feature names, but no working current-event backend was established. YouTube
returned403; no video was watched. See docs/research.md for source links.
