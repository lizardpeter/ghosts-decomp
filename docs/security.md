# Security issues to fix in the enhanced build

Known vulnerabilities in Ghosts and in the IW-engine code it shares, for the enhanced build (docs/variants.md).
The faithful build keeps them. Sources: the community clients' fixes (docs/community-patches.md) and public
reports (surveyed 2026-10; verified facts and inferences are kept separate below).

## Public record

- **CVE-2018-20817** names Ghosts explicitly, together with MW2, MW3, AW, BO1 and BO2 before 2015-08-11:
  `SV_SteamAuthClient` copies the Steam `authBlob` from a connecting client into a fixed buffer without a size
  check, which allows remote code execution on the host. The Steam MP build (2018) postdates the fix date; the
  server references (2014) predate it, but console-host servers don't use Steam auth (the function is absent from
  the PS4 server PDB). Whether the Store build has the fixed version is to be checked once it is matched.
- **CVE-2019-20893** (MW2 2009): `PartyHost_HandleJoinPartyRequest` overflows on a crafted join-party packet. Ghosts
  has the same party-host lineage; inference, to verify in the client code.
- **CVE-2018-10718** (MW2 2009, unnamed function, crafted packets) and the id Tech 3 classics (`CL_ParseDownload`,
  CVE-2006-2875, server overflows client) are bug *classes* to audit in the netcode, not confirmed Ghosts bugs.
- Takedowns: MW2 (2009) PC multiplayer went offline in July 2023 over a self-spreading P2P exploit; WWII PC in July
  2025 over in-match RCE. No report of Ghosts PC being taken offline was found.

## Fix list

Location in the PS4 server reference where the function exists there (server-side code); `client` means the
function is client-only and will be located in the Store build by matching.

| # | Function | Bug | Vector | Fix (enhanced) | Where (PS4 server) | Source |
|---|---|---|---|---|---|---|
| S1 | `SV_SteamAuthClient` | unchecked `authBlob` copy (RCE) | connecting client → host | bound the copy | not in server; client/host | CVE-2018-20817 |
| S2 | `PartyHost_HandleJoinPartyRequest` (name from MW2) | overflow on join request (RCE in MW2) | lobby peer → host | bound/validate | client | CVE-2019-20893 (inferred for IW6) |
| S3 | `NET_DeferPacketToClient` | packet copy without length clamp | network peer | clamp to the destination size (iw6-mod: 1262) | 1401A11D0 `qcommon/net_chan_mp.cpp:1615` | iw6-mod network.cpp |
| S4 | `SV_ExecuteClientMessage` | negative `reliableSequence - reliableAcknowledge` hangs the server | client → server | reject/clamp | 1401F3680 `server_mp/sv_client_mp.cpp:5068` | iw6-mod security.cpp |
| S5 | `SV_AddBot`, `SV_AddTestClient` | `sprintf` into fixed name buffers | server config/script | bounded formatting | 1401F1890 `:5458`, 1401F1AF0 `:5276` (`sv_client_mp.cpp`) | iw6-mod security.cpp |
| S6 | `PlayerCards_SetCachedPlayerData` | unchecked indices | server/peer → client | bounds 0..17, 0..41 | client | iw6-mod security.cpp |
| S7 | `UI_ReplaceDirective` | unchecked source length | server HUD text → client | reject > 0x100 | client | iw6-mod security.cpp |
| S8 | HudElem enum-string `sprintf` | 0x800 buffer overflow | server/script → client | bounded formatting | client | iw6-mod security.cpp |
| S9 | OOB `print` handler | any internet host prints into the client | any host | accept only from the connected server | client | iw6-mod network.cpp |
| S10 | `Cmd_LUINotifyServer` | non-host sends `end_game` | client → server | host only | server-side handler, to locate | iw6-mod patches.cpp |
| S11 | server-pushed dvars | flags not enforced, saved dvars overwritten | server → client | enforce flags, refuse `DVAR_SAVED` | client | iw6-mod dvar_cheats.cpp |
| S12 | `fs_game` from the server | path traversal (`..`, `::`) | server → client | restrict to `mods/`, reject traversal | client | iw6-mod mods.cpp |
| S13 | PlayerData lookup strings | unvalidated reserved lookups crash the client | server/stats → client | validate | client | iw6-mod stats.cpp |
| S14 | Havok Script (LUI) | `io`, `os`, `package`, `debug`, `loadfile`/`dofile`/`load`, `string.dump`, `os.execute` reachable | malicious mod/fastfile/UI | don't open the libraries | client | iw6-mod ui_scripting.cpp |
| S15 | fastfile loading | signature check (kept in the original; the community clients disable it) | server-supplied/mod fastfiles | keep a signature check (our own key) | both | docs/community-patches.md §2 |
| S16 | crash fixes | null `g_entities` on "invalid password" kick; migrated-client reconnect with duplicate GUID; atexit crash | server/client | null checks, clean rejection | partly server-side, to locate | iw6-mod patches.cpp, network.cpp |

## Audit targets (no known bug yet)

The community fixes are reactive. For a reconstruction, every function that parses network or file input gets a
bounds review as it is decompiled: `MSG_Read*` (e.g. `MSG_ReadData` 14019D1B0 `qcommon/msg.cpp:1030`), Huffman
decoding, gamestate/configstring/snapshot parsing, `SV_DirectConnect` (1401F25B0), `SV_PacketEvent` (1401FA920),
party/lobby messages, voice packets, stats/PlayerData, fastfile and asset parsing. Findings are recorded here with
a test that demonstrates the original behaviour.
