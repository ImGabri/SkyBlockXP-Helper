# Classic Event and Solara research

Research performed during this task on 2026-11-01. The requested target is the
Halloween **Classic Event within PS99**, according to the user's clarification.
The user's in-event client-log screenshot records **place `85920622393590`**
and **universe `3317771874`**. These are client-observed IDs, not an independently
verified official event announcement. The official Update99/100 pages were subsequently checked and confirm the
PSX Classic/Halloween target. Its current scripting interfaces remain unverified. Older standalone PSX APIs are not used
as evidence for this event.

## Official event sources now verified

After the environment network update, official pages returned HTTP200:

- [Update99, PSX Classic!, October24,2026](https://www.biggames.io/post/pet-simulator-99-update-99)
  confirms the real PSX event inside PS99, its portal, Spawn/Fantasy progression
  and classic rewards. This matches the user's target description.
- [Update100, Halloween Games!, October31,2026](https://www.biggames.io/post/pet-simulator-99-update-100)
  documents the Halloween content and the PSX Classic Halloween update.
- Main PS99 listing: https://www.roblox.com/games/8737899170/Pet-Simulator-99
- User-observed event destination: https://www.roblox.com/games/85920622393590/

The earlier CONNECT403 failures were real at the time. Public rscripts/BIG Games
requests now succeed after the network revision. YouTube requests still returned
HTTP403, so no video was watched or transcript verified.

## Public examples

[GitHub Classic searches](https://github.com/search?q=ps99+classic&type=repositories)
and [public autofarm searches](https://github.com/search?q=ps99+autofarm+language%3ALua&type=repositories)
did not establish current, readable event interfaces. Search results included
outdated or obfuscated scripts and programs that performed mailbox transfers
rather than farming. None were executed or incorporated. No reference reviewed
verifies current Classic Event behavior. Subsequent legacy interface evidence
is documented below.

## User diagnostic and legacy interface reference

The user subsequently supplied an in-event diagnostic showing Library as a
ModuleScript, Library.Client with PetCmds/Network/WorldCmds, and __THINGS folders
Coins, Orbs, Lootbags and __REMOTES. ReplicatedStorage contains generically named
RemoteEvents. Those names do not identify command signatures.

A readable [legacy reference pinned to commit 3f715a0](https://github.com/Cypaex/Pet-Simulator-X-Autofarm/blob/3f715a0351d68df9af454a2cdadfaf3ec01bef99/Engine),
dated 2023-07-18, documents these interface facts:

- PetCmds.GetEquipped() yields pet records with uid (lines 1060–1066).
- Network.Invoke("Join Coin", coinId, {uid}), then
  Network.Fire("Farm Coin", coinId, uid) (lines 1065–1066).
- Network.Fire("Claim Orbs", orbNameArray) (line 831).
- Network.Fire("Collect Lootbag", lootbagName, playerPosition) (line 842).
- The client coin dictionary has p position, a area, n coin type, health,
  and pets records; loaded coin Models contain a Coin BasePart.

The Get Coins remote name appears at line 412, but the source does not consume
its response: it extracts its coin dictionary using private client upvalues.
Therefore its Get Coins response schema is **not verified** by this reference.
The reference also ignores Join Coin's return; acknowledgement semantics are
unknown. Our counters report requests, not confirmed assignment/rewards.

The reference has no license file. No source code was copied. Its hooks,
private-upvalue extraction, metamethod changes and unrelated features were not
incorporated. The implementation is original and only attempts native module
access. A table/function existing does not prove current command compatibility.

Version 0.3 adds a guarded compatibility attempt: require the concrete current
client modules, verify expected exports, then make one Get Coins request and
validate a nonempty dictionary against actual loaded coin Models. Only matching
responses enable experimental features. A rejection or schema mismatch disables
the adapter; it never falls back to generic RemoteEvents or a bypass. This is
an executable compatibility probe, **not a completed live-event validation**.

## First live probe and return-value handling

The user's v0.3 screenshot confirms that the UI loads and the probe reaches the
Get Coins response check, where its first return is not a table. It does not
establish whether the command returned nil, a status flag, or another type.
The UI's zero equipped-pet count is a default: this failure happens before the
equipped-pet read, so it does not mean the user has no equipped pets.

Code review found that the pcall wrapper kept only one return value. Version
0.3.1 fixes this independently demonstrated bug and accepts either a direct
dictionary or an exact true-plus-dictionary tuple after strict loaded-coin
validation. No source reviewed proves that the live event uses that tuple.
Nil, zero returns, false status and malformed values remain blocked. Diagnostics
show only response count/types, plus exported API names/arities; successful
scalar payload contents are not dumped. A new live run is required to diagnose
the actual event response rather than assuming the screenshot's cause.

## Confirmed zero-value response and supplied console log

The later v0.3.1 screenshot reports `returns=0; types=none`: the call returns no
values. This rules out a hidden second tuple value as the cause of that run.
The first uploaded client log contains 4095 lines and 512 repeated warnings:
`Debug|Network|Invoke 'getgenv' [Get Stats]`, with Network._check and Save.FetchPlayer
in the stack. There are no Get Coins response/export diagnostic lines in that
retained console history. The full private log is not committed.

The second log has 4096 lines, 511 Get Stats warnings and one direct Get Coins
warning: callerScript:err: Client.Network:306 assertion failed, through _check
at line 375. That directly establishes a caller-script validation failure for
Get Coins. It does not prove that another network provider would work. No guard is disabled and an empty reply is never
turned into a fabricated coin snapshot. Version 0.4 removes automatic probing
at startup and retains an explicitly requested manual check.

## Requested feature references and access limits

The user identified https://rscripts.net/game/pet-simulator-x and asked for video
references covering map-wide farming, hatching from anywhere, auto-gold and
auto-rainbow. The rscripts index now loads. Its advertised feature lists were inspected;
YouTube still returned403, and no video content was watched. The following
readable/public references were checked without executing third-party loaders:

The readable Cypaex reference does not demonstrate those unrestricted features:
its farming filters by CoinGrabDistance and unlocked area (lines948/976), and its
Buy Egg call is preceded by unlock/world checks and travel within30studs of the
egg (lines1167–1206). Public gold/rainbow and auto-hatch candidates inspected were
obfuscated. No current conversion or remote-hatching contract was verified.
A normal-input macro can operate only the visible client and cannot provide
remote map-wide behavior. That alternative was paused rather than presented as
feature-equivalent.

## Additional public source findings

- [Daycare & Auto-Farm,2026-04-09](https://rscripts.net/script/pet-simulator-x-or-daycare-and-auto-farm-rJcJ)
  advertises farming/hatching and Gold/Rainbow menus. Its code is a key-based
  external loader; that listing is not proof of current Classic Event support.
- [OP Script,2023-02-25](https://rscripts.net/script/pet-simulator-x-op-script-3450)
  advertises conversion features but links an obfuscated Galaxy loader.
- [Hylician pinned source,2023-07-10](https://github.com/Hylician/Pet-Simulator-X/blob/de93a64312ff41a05b0c69b1afe04099f8ab356b/source)
  documents Buy Egg and machine requests with same-species pet UID arrays.
  Its networking is modified using private upvalues; it is not a native-compatible
  fix for the current caller assertion. No license is declared; no implementation
  was copied.
- [Gavin pinned archive,2022-07-04](https://github.com/gavinnn101/RobloxExploitScripts/blob/1a9e0192e14851c032b58c3c6460d80313a5f500/PetSimulatorXArchive/PetSimX.lua)
  directly consumes Get Coins as a dictionary and uses historical lowercase
  machine-command names. No current-event compatibility or license is established.
- [A current-looking PS99 source,2026-10-28](https://github.com/DarkSwarm123/Pet-Simulator/blob/521b606cbf19b47c1933e82eb0af0a91539e129c/Pet%20Simulator%2099.lua)
  explicitly excludes event place 85920622393590. Its PS99 interfaces are not
  Classic Event evidence.

## Solara compatibility evidence

There is no authoritative, current Solara capability matrix in the sources
reviewed. A function's existence does not prove it works in a given client.

- [UNC NamingStandard](https://github.com/unified-naming-convention/NamingStandard)
  says the convention is retired; executors may support different subsets.
- [UNC instances](https://github.com/unified-naming-convention/NamingStandard/blob/main/api/instances.md),
  [filesystem](https://github.com/unified-naming-convention/NamingStandard/blob/main/api/filesystem.md)
  and [miscellaneous](https://github.com/unified-naming-convention/NamingStandard/blob/main/api/misc.md)
  document optional executor conventions; they are not Solara guarantees.
- [Hydroxide issue 116](https://github.com/Upbolt/Hydroxide/issues/116) and
  [Parvus issue 64](https://github.com/AlexR32/Parvus/issues/64) contain 2024 reports
  about Solara hook compatibility. These historical reports do not establish
  compatibility for current Solara versions or this event.

The implementation uses native Instance UI in PlayerGui, ordinary Roblox
services, and a single bundled source file. It does not require Drawing, getgc,
hookfunction, hookmetamethod, newcclosure or a remote UI loader. Clipboard and
idle input are optional, protected calls. In-game testing remains required;
compilation and mocked-boundary checks do not establish Solara support.

## Remaining evidence

1. Review a readable current-event implementation or supported native interface.
   The supplied index and official event posts have now been reviewed; available
   public sources do not verify a working current Classic Event backend.
2. Compare a candidate interface against the observed caller-script rejection.
   A legacy feature list or menu screenshot cannot establish current support.
3. Establish a working, non-empty current interface before enabling farming,
   hatching or conversions. Current reported native probe acceptance is FAILED.
4. Verify actual game-side actions, rewards, cancellation, respawn and cleanup
   in the client. Local fixture tests establish only local code guarantees.
