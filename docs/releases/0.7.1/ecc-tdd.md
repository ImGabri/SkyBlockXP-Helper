# v0.7.1 — machine approach and current coin-shape recovery

The user reported real gold/rainbow range failures and supplied shared-chat
diagnostics plus commit89e9fc1. The commit and its parent were preserved in merge
2043559, retaining passive preflight, visible stages and worker state. The shared
chat was read successfully; embedded hotfix code was not executed.

## Test-first checkpoints

| Guarantee | RED | GREEN |
| --- | --- | --- |
| Preserve server rejection reason; definite range rejection does not strand six pet UIDs |1e71868:2 failures|fc3845b:18 care methods pass|
| Guarded h/POS coin support, strict dual health, explicit per-UID join and stale phase isolation |395d503:12 case failures|6a7bc08:50 adapter methods pass|
| Walk before mutation/menu action, arbitrate movement, recognize l/gift protection |583157b:5 failures|b8a8a7d:20 runtime+18 care pass|
| Resolve correct loaded Pad, walk/pathfind, verify actual arrival, stop/cancel/dead-owner handling |60848e7:14 methods/24 failing cases|e08cad5:all pass|
| Machine buttons and canonical Walk/Off setting |cb5710a:2 UI failures|1a269d1:6 UI methods pass|
| Loader/Save stage is visible before a native call yields |5606b43:2 failures|3c26cda:20 care pass|
| Explicit Go pauses farming even in Off mode; pet-tool reload halts native movement |f318069:2 failures|83d247d:22 runtime pass|
| Nearby Jump waypoint still triggers a jump |de381c9:reproduced failure|245f6d1:15 navigation methods/25 cases pass|
| No journey without six eligible pets; re-read eligibility after travel |daaf321:2 failures|d5790ff:21 care+23 runtime pass|

Actual commands: affected `python3 -m unittest tests/test_care.py`,
`tests/test_adapter.py`, `tests/test_runtime.py`, `tests/test_interface.py` and
`tests/test_navigation.py`, including focused RED selections. All checkpoints
remain reachable on the active branch; no history was squashed.

Independent review reproduced three movement bugs (Off-mode competition, reload
movement leak and nearby Jump skipping). All were fixed with regression tests;
the reviewer reran affected Runtime/navigation suites successfully. No live client
or server acceptance was inferred from review.

## Final verification

`python3 scripts/build.py` and `bash scripts/check.sh` passed:
127 Python methods (50 adapter,12 builder,21 care,6 UI,15 navigation,23 runtime),
11 policy,9 jobs and16 conversion-policy tests: **163 passed,0 skipped**.
All12 source/bundle/helper files compile. Rojo builds the Studio place and all10
packaged source properties exactly match the checkout. Strict pure-module typing,
Bash syntax, Git whitespace and a limited tracked-file credential-pattern scan
pass. No full Roblox client type/lint gate is configured.

Executable-line Luau fixture measurements: PetCare262/266 (98.5%),
Runtime387/478 (81.0%), Interface399/438 (91.1%), coin394/444 (88.7%),
navigation107/109 (98.2%). Measurement helpers/results are retained outside the
repo under `/workspace/.tools/psx-coverage-v06`, `psx-navigation-coverage` and
`psx-current-reference`. These are not branch, live rendering or gameplay coverage.

## Target acceptance

The user's prior build FAILED at range/initialization. **v0.7.1 target acceptance
is NOT PERFORMED**: this environment has no attached Roblox/Solara client. The new
workflow addresses concrete missing local steps but cannot guarantee current
server distance, commands, chance, world layout or farm success. Eight studs is
our conservative arrival target; no authoritative server threshold was obtained.

Next executed target check: fresh Classic Event client → load this version →
Pets/Load pet tools → open Inventory/select species → keep Machine travel=Walk →
manual GoldOnce/RainbowOnce near a loaded unlocked machine. Missing pads, failed
paths or server reasons are surfaced. A batch is checked before movement and
again before submitting; no unknown or rejected request is automatically replayed.
