# v0.5.0 — public-library compatibility candidate

The user asked to make the Classic Event suite functional after the v0.4 native
Get Coins route returned zero values and logged a caller-script assertion.
Journeys were derived from that failure and the documented public Library and
original module-loader interfaces, using ECC tdd-workflow and verification-loop.
This release changes the failing integration point; it is not a live-verified
automation suite. Hatching from anywhere, auto-gold and auto-rainbow remain open.

## Test-first evidence

All checkpoints are reachable on the active `work` branch; none were squashed.

| Guarantee | RED checkpoint and observed result | GREEN checkpoint and result |
| --- | --- | --- |
| Use the public Library ModuleScript, prefer the original loader when exposed, avoid private fallback on rejection, report proxy methods, stop after canceled loading | `e20418d`, `f2bfbc3`: six new methods failed for missing behavior, existing 35 passed | `8237e88`: all 41 adapter methods passed |
| Stop between lazy facade lookups and prevent stale facade/export work replacing a newer connection | `eee3117`: four failures across three new methods, including both cancellation subcases | `3632966`: all 44 adapter methods passed |

The actual RED/GREEN command was `python3 -m unittest tests/test_adapter.py`.
Tests execute the real adapter bundled with explicit Roblox-boundary fixtures
under Luau0.745. They establish local resolution, dispatch and cancellation
behavior; fixture-supplied game responses do not establish server acceptance.
An independent read-only reviewer reproduced the stale-state regression and
reran all44 methods after the correction, finding no remaining material blocker
in the loader/facade change.

## Local verification

- `python3 scripts/build.py` and `bash scripts/check.sh` passed:66 Python test
  methods (44 adapter,12 builder,8 runtime,2 interface),11 policy and8 job tests;
  **85 passed,0 skipped**. Some adapter methods include multiple fixture cases.
- All9 source/bundle/helper files compile; Rojo builds the Studio place. An XML
  comparison of every Source property matches all7 current Luau sources exactly.
- `.tools/bin/luau-analyze src/client/Config.luau src/client/Policy.luau`, Bash
  syntax and `git diff --check` pass. No full Roblox type definitions or project
  formatter/linter are configured; full client type/lint validation is unmeasured.
- A limited tracked-file credential-pattern scan found no matching tokens or
  private keys. This is a pattern check, not a security audit.
- The generated standalone bundle contains the same loader and cancellation
  changes as the module sources; it does not load another script at runtime.

Luau `--coverage` was run against all44 adapter methods (57 fixture executions),
aggregating executable line hits within the bundled PetSim99 source section:
**357/370 executable lines,96.5%**. The diagnostic measurement helper is retained
outside the repository at `/workspace/.tools/psx-coverage-v05/measure.py`; its JSON
result is adjacent as `adapter.json`. Pure-module coverage was also remeasured:
Jobs45/48 (93.8%), Policy51/53 (96.2%). These are executable-line measurements,
not branch, full-client, executor or real-game coverage.

## Target acceptance

**NOT PERFORMED for v0.5.0.** This environment has no running Roblox/Solara client.
The last executed live check was FAILED on the older direct-client-module route:
Get Coins returned `returns=0; types=none` and the supplied log recorded the
caller-script assertion. The new public route may still reach the same guard.
No guard is disabled, empty reply fabricated, or successful action inferred from
a dispatched request.

The next check requires the user's fresh Classic Event client: execute v0.5.0,
run Farm → Run compatibility check once, then test Nearest farming only if the
probe succeeds. The report now identifies the selected Module loader and Network
provider. Continued zero returns or rejection leave automation disabled.
