# Classic Event and Solara research

Research performed during this task on 2026-11-01. The requested target is the
Halloween **Classic Event within PS99**, according to the user's clarification.
The user's in-event client-log screenshot records **place `85920622393590`**
and **universe `3317771874`**. These are client-observed IDs, not an independently
verified official event announcement. The official update name, mechanics and
network interfaces remain unconfirmed. Older standalone PSX APIs are not used
as evidence for this event.

## Official sources still blocked

- BIG Games: https://www.biggames.io/
- PS99 listing: https://www.roblox.com/games/8737899170/Pet-Simulator-99

Both requests failed at the environment's HTTPS proxy with `403 Forbidden`
before their contents could be read. That Roblox URL identifies the known PS99
listing, not a verified Classic Event destination. Required domains were added
to the environment draft; draft saving does not activate network changes.
The reported event destination is
https://www.roblox.com/games/85920622393590/ (URL derived from the observed ID;
its page contents have not been read). A current module diagnostic is still
needed from inside that place.

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

To implement current event farming:

1. Read the official event announcement once network access is active.
2. Run version 0.3 in the event beside loaded coins and record the probe result.
3. If the probe passes, test one farm cycle and confirm actual game-side pet
   assignment/coin damage; test collection by observing game-side rewards.
4. Verify disappearing targets, respawn, cancellation, repeated execution and
   unload in the actual client. Mocked tests cannot establish those live outcomes.
