# v0.12.0 — merged input farming and guarded pet workflows

The release preserves both concurrent lines of work. A normal push of the
intermediate v0.8 build advanced `pet-sim-classic-automation` to `ab3314e`, but
GitHub rejected the `main` update because another chat had published v0.11.0
at `ff56282`. No force push was used. Merge `40d5677` combines both histories;
v0.12.0 includes the B-key detected-target input farm and the egg/machine walking
workflows. The earlier v0.8 evidence remains an intermediate checkpoint.

## Local defects reproduced and fixed

The explicitly requested ECC TDD and verification workflows were used. Each RED
checkpoint below was executed before its corresponding production change.

| Local guarantee | RED checkpoint | GREEN checkpoint |
| --- | --- | --- |
| Input requires positive focus, native cursor coordinates, no text/menu focus and a clear PlayerGui hit test | `de73de4`: 10 methods, 37 failing fixture cases | `c4c3120`: focused guard cases pass |
| Rejected module-mode changes and stale save inspections cannot alter current ownership; Direct lazily loads only the selected public WorldCmds child | `d4dd972`: 5 failing cases | `46d9546`: 93 adapter/care methods and 4 joint workflows pass |
| Pet jobs take priority over input; death/care discard cached aim; generic settings cannot activate a rejected input option | `79c8325`: 5 failing cases | `e426e70`: 40 Runtime methods and 4 joint workflows pass |
| CanvasGroup rendering transparency cannot hide input-active descendants from the guard | `f6bacbc`: 4 failing fixture cases | `2872ff0`: 12 guard methods and 40 Runtime methods pass |

Input checks run before aiming and again before clicking. A world Mouse.Target
match alone does not clear GUI input interception. Transparent groups may hide
rendered descendants while those descendants remain interactive. Unsupported or
ambiguous native GUI/focus queries pause input. These checks are not an atomic OS
input transaction and do not establish complete protected CoreGui coverage.

Pet actions share one worker slot. Walking uses ordinary pathfinding and keeps
character, target and actual proximity guards active through yielding native
reads immediately before submission. Direct preparation loads four known modules;
WorldCmds is resolved lazily for the selected egg workflow. A canceled preparation
token is not reused by a later operation. No automatic Facade fallback or native
remote replay was added.

## Verification

`python3 scripts/build.py` and `bash scripts/check.sh` pass:

- 195 Python methods: 55 adapter, 12 builder, 38 care, 12 input guard, 6 UI,
  28 navigation, 40 Runtime and 4 integrated pet workflows.
- 13 policy, 9 job and 16 conversion-policy cases.
- **233 total passed, zero skipped.** All 13 source/bundle/helper files compile.
- Rojo builds the Studio artifact; its 11 Source properties match the checkout
  exactly. Bundle freshness, strict Config/Policy/ConversionPolicy typing,
  Bash syntax and Git whitespace checks pass.
- A limited tracked-file GitHub-token/private-key pattern scan finds no matches.
  This is not a comprehensive security audit. Full Roblox client typing and a
  project lint gate remain unconfigured.

Executable-line boundary-fixture coverage is PetCare 424/434 (97.7%), Runtime
780/971 (80.3%), Interface 418/457 (91.5%), adapter 471/497 (94.8%), navigation
139/141 (98.6%) and ClickGuard 80/82 (97.6%). Measurement helpers/results are
retained outside the project in `/workspace/.tools/psx-coverage-v06`,
`psx-navigation-coverage` and `psx-click-guard-coverage`. These measurements do not
cover real rendering, OS input, Roblox geometry, branch coverage or rewards.

A separate final reviewer found no material regression in the input guard,
care/input ordering, navigation ownership or Direct lazy module resolution.
The reviewer reran 56 focused guard/Runtime/joint-workflow methods, checked
bundle freshness and reviewed the README/UI against the implementation.

## Reference and target acceptance

The user-supplied paste decrypts to the same FlowAuth loader supplied directly.
Its readable launcher handles authentication and transport; the public runtime
is obfuscated. Static inspection yielded no usable game-specific farming,
hatching or conversion contract. Nothing was executed or incorporated from that
payload. See [research](../../research.md).

**Reported live native contracts: FAILED.** The user's latest evidence says
Get Coins returned no values, inspected coin Models numbered zero and Save.Get
returned nil. Successful module loading does not override those failures. Native
pet operations stay blocked without a valid public save; the input farm does not
depend on that backend.

**Combined v0.12.0 target acceptance: NOT PERFORMED.** No Roblox/Solara client is
attached. Local tests do not prove that breakables receive attacks, purchases
succeed, current machine range is accepted or six pets guarantee 100% chance.
The server controls access, chances, prices and range.

Next permitted live check: run the published build in a fresh Classic client,
confirm the version, test B with menus closed and the panel hidden, then stop it.
Inspect the save read-only before trying native pet tools. A new nil/rejected
result remains an actual failure; do not repeatedly probe the rejected route.
Readable source from the reference author or new authorized in-game diagnostics
would be needed to compare its hidden adapter. No script key is required for
continued local development.
