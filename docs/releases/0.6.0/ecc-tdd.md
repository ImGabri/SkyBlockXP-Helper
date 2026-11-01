# v0.6.0 — egg tools, six-pet conversions and product naming

The user requested egg opening, gold/rainbow conversion with six pets, native-menu
shortcuts, quality-of-life controls and public GitHub renaming. User journeys
were derived from that request and pinned legacy interface research. ECC's
test-first workflow and verification loop were applied; repository conventions
were preserved. No third-party implementation or loader was executed/copied.

## RED/GREEN checkpoints

All checkpoints are reachable on `work`; none were squashed.

| Observable guarantee | RED | GREEN |
| --- | --- | --- |
| Exactly six unique eligible same-species Normal→Gold or Gold→Rainbow pets; deterministic grouping | `dc6c7f8`:16 failing tests for missing NextBatch | `e8a9099`:16 pass, strict typing pass |
| Four tabs, pet controls/actions, canonical option rendering and status counters | `d4de779`:6 failing UI methods | `cc9b9bf`:6 pass |
| Real public-library hatch/machine signatures, protected/duplicate exclusions, reservations, menus and cancellation | `5b096f9`:12 methods/33 failing cases | `1cb8287`:13 methods pass including lock evidence |
| Missing or locked native inventory slots never permit conversion | `53aba65`:2 failing cases | `1cb8287`:both pass |
| Pet controls work independently of failed coin probe, with one cancellable mutation slot | `5ad35a7`:3 new runtime failures; prior8 pass | `977453d`:11 runtime methods pass |
| Successfully canceled native worker releases its owner; slow conversion cannot starve other stages | `c7694a9`:both regressions reproduced | `20f3718`:14 care+12 runtime methods pass |
| Directory selector buttons dispatch correct actions | `2c1d723`:UI callback failure | `6e5f5cf`:6 UI methods pass |
| Select loaded eggs/species without spending; support numeric species directory keys | `b01b1f6`:3 failing methods | `a2f80b5`:16 care+13 runtime methods pass |

Commands actually run: `python3 -m unittest tests/test_care.py`,
`python3 -m unittest tests/test_runtime.py`,
`python3 -m unittest tests/test_interface.py` and
`.tools/bin/luau tests/conversion_policy.luau`, including focused RED selections.
Temporary test-only stand-ins allowed missing-feature tests to compile and fail
at the intended assertion. There are no stand-ins in the shipped implementation.

Characterization commit `5afb7bc` adds failed-operation reporting, no-overlap
preparation, respawn cancellation, clipboard fallback/recovery and rejoin cleanup.
All17 runtime methods pass; no new production bug or artificial RED is claimed
for these existing-behavior checks.

## Verification and limits

The integrated check surface is `bash scripts/check.sh`: Python boundary/bundler
tests,11 policy tests,8 job tests,16 conversion-policy tests, bundle freshness,
all source/bundle compilation and Rojo Studio packaging. Extra checks include
strict Config/Policy/ConversionPolicy typing, Bash syntax, Git whitespace, an
exact XML Source comparison and a limited tracked-file credential-pattern scan.
No full client type/lint gate or Roblox type environment is configured.

Final integrated result: **95 Python methods +11 policy +8 job +16 conversion
tests =130 passed,0 skipped**. All11 source/bundle/helper files compile; the
Studio package contains all9 source files exactly. Static checks listed above
pass. No real-game acceptance follows from these local results.

Actual Luau `--coverage` measurements aggregate each bundled source section across
the corresponding boundary fixtures:

| Module | Covered executable lines | Percent |
| --- | --- | --- |
| PetCare |217/221|98.2%|
| Runtime |325/388|83.8%|
| Interface |392/431|91.0%|
| Coin adapter |357/370|96.5%|
| ConversionPolicy |44/44|100%|

The four client measurements were rerun via
`/workspace/.tools/psx-coverage-v06/measure.py`; adjacent `report.json` retains the
results. These are executable-line measurements, not branch coverage, rendered
Roblox UI tests or real gameplay. The old pure Job/Policy modules were unchanged
and their previous line results remain recorded in v0.5 evidence.

Independent review reproduced a dead-owner busy latch, which was fixed and tested.
A fresh read-only reviewer subsequently found no remaining release blocker in
PetCare or Runtime/Jobs, reran affected tests and checked pending timeout/respawn
behavior. Review does not establish server acceptance.

## Game acceptance

**NOT PERFORMED for v0.6.0:** no Roblox/Solara client is connected to this cloud
workspace. The last supplied live coin check failed with zero values and a
caller-script assertion. Current public-loader, egg/machine, range, inventory
schema and menu acceptance remain unverified. A true reply is acknowledgement,
not proof of a resulting pet or reward. No current100% chance is promised.

Next target check: fresh Classic Event client → load v0.6 → Pets/Load pet tools →
Next egg + Open egg once → open Inventory + select species + manual six-pet
conversion → enable the corresponding auto feature only after checking results.
Unavailable menus and unknown/rejected responses report errors and stay stopped.

## GitHub/product changes

The repository was already public. The rename API returnedHTTP403,
`Resource not accessible by integration`, despite the actor's visible admin role.
Changing repository name/description/topics therefore requires repository
administration write capability or an owner action in GitHub settings. No token
was requested or inspected. The existing main tip was fetched and verified as an
ancestor so publication to main can be a normal fast-forward, preserving history.

Canonical artifacts/UI/Studio/session names now use `PetSim99AutomationSuite`.
The old session marker is recognized only to unload older releases. Historical
release documents retain their actual prior artifact names.
