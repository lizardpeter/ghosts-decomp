# GDK runtime calls in iw6mp64_MSStore_ship

Scope: the 97 xgameruntime.lib thunks listed in the thunk table below, plus the runtime start-up helpers around them.
Sources: Ghidra pseudocode, disassembly and callgraph in analysis/iw6mp64_MSStore_ship, and the IIDs and .rdata read
from the original exe with pefile. Reconstructed functions are now executed against the original in an emulator
with modeled OS and SDK providers; no service is contacted. The names are in records/names.tsv
(method `gdk-thunk`); docs/network.md puts them in context.

## Summary

- **All 97 thunks are named; none is left `sub_<VA>`.** Confidence: 12 at 0.95, 14 at 0.9, 47 at 0.85, 13 at 0.8,
  1 at 0.75, 7 at 0.7, 3 at 0.6. Five runtime helpers outside the table also have behavior identifications.
  The three internal helpers retain `sub_<VA>` source names because their original names are unknown.
- **The 13 interfaces.** Each thunk calls `QueryApiImpl(&familyIID, &versionIID, &api)`. The IID in the thunk table below is
  the *version* IID, the second argument. Families: XUser 01ACD177 has two versions (079415E3 and CEF4FAC0), XGameSave
  704C3F58-...6FE2 / ...6EE2, XStore 0DD112AC / 5C48DEDF, XNetworking 37E56907 / BF2346B2, XPackage AF406016 / E2A4734B,
  XGameUI DFCD4649 / 36A03122, XSystem E349BD1A / DADC2895, XGame 973A344E / 2549F142. Core, XGameInvite,
  XGameRuntimeFeature and XGameEvent use the same IID for both arguments.

| IID (version) | Interface | Thunks |
|---|---|---|
| 079415E3 | XUser | 24 |
| 073B7DCB | XAsync + XTaskQueue + XThread (one core interface: slots 0x18-0x58 XAsync, 0x60-0xc8 XTaskQueue, 0xe8 XThread) | 18 |
| 5C48DEDF | XStore | 16 |
| 704C3F58 | XGameSave | 12 |
| BF2346B2 | XNetworking | 10 |
| E2A4734B | XPackage | 8 |
| 36A03122 | XGameUI | 2 |
| 0651AAE2 | XGameInvite | 2 |
| CEF4FAC0 | XUser (newer version, XUserGetGamertag with component) | 1 |
| 2549F142 | XGame | 1 |
| DADC2895 | XSystem | 1 |
| 8836FE87 | XGameRuntimeFeature | 1 |
| BBFBDCC7 | XGameEvent | 1 |

- **Slot order follows the header order.** It was checked against the anchored functions. In XUser: 0x18
  DuplicateHandle, 0x20 CloseHandle, 0x28 Compare, 0x38/0x40 AddAsync/AddResult (string-anchored), 0x48 GetLocalId and
  0x58 GetId (string-anchored), then GamerPicture, AgeGroup, CheckPrivilege, ResolvePrivilege, TokenAndSignature and
  ResolveIssue in header order. In XAsync: GetStatus, GetResultSize, Cancel, (Run), Begin, (BeginAlloc), Schedule,
  Complete, GetResult. Functions added in later GDK releases sit at the end of the vtable: XUserIsStoreUser 0x150,
  XStoreShowProductPageUIAsync 0x258, and probably XPackage 0x128-0x140.
- **The game's GDK layer is 14019F3A0-1401A9640.** It is Activision's own code ("GDK tasks.", "GDK users tasks.",
  "GDK gamesave tasks.", "GDK presence tasks.", "GDK session tasks.", "GDK store tasks."). Every GDK task runs through
  the game's TaskManager (14045F1F0 construct, 14045F3B0 alloc, 14045F4F0 frame). The other callers are statically
  linked Microsoft libraries:
  - **XSAPI** (Xbox Live C API, 1406D0000-1406FF000): User wrapper, events, social, GlobalState.
  - **libHttpClient** (1407B0000-1407F4000): HC_CALL, NetworkState, WinHttpProvider, CurlProvider, XCurlMulti.
  - **Demonware**: bdHTTPWorker(WinHTTP) 1407CCBF0-1407CF690, bdHTTPAuthService 140749EF0/14074A030, and a Demonware
    GDK task class 140762430-1407628B0 that does its own XUserAddAsync and token request.

## Network and Xbox/Microsoft services

These thunks can produce traffic, either themselves or through the Xbox app or Gaming Services (the "network?" column
below):

- **Sign-in and accounts (MSA/XSTS through Gaming Services):** XUserAddAsync/Result, XUserResolveIssueWithUiAsync/Result
  (the game passes "https://www.xboxlive.com"), XUserResolvePrivilegeWithUiAsync/Result, XUserGetGamerPictureAsync and
  its results.
- **Token requests:** XUserGetTokenAndSignatureAsync/ResultSize/Result.
  - Demonware 140762780 requests a token for `POST https://auth3.prod.demonware.net`. This is how the game logs in to
    Activision's backend.
  - XSAPI 1406F6B00 requests tokens for every Xbox Live REST call.
- **Licence checks (Microsoft Store):** XStoreQueryGameLicenseAsync/Result, XStoreQueryAssociatedProductsAsync/Result,
  ProductsQueryNextPageAsync/Result, XStoreAcquireLicenseForPackageAsync/Result (DLC), XStoreShowProductPageUIAsync.
- **Cloud saves (Connected Storage):** XGameSaveInitializeProviderAsync/Result (SCID
  00000000-0000-0000-0000-000066cdd1f0, syncOnDemand=true), XGameSaveReadBlobDataAsync, XGameSaveSubmitUpdateAsync.
- **Achievements and stats:** XGameEventWrite. 14019F3D0 writes "Achievement<N>Unlocked" events with `{"Unlock":true}`
  through XSAPI XblEventsWriteInGameEvent (1406D1880), which ends in XGameEventWrite.
- **Security info for URLs:** both XNetworkingQuerySecurityInformationForUrl families and XNetworkingVerifyServerCertificate.
  They are used by libHttpClient and by bdHTTPWorker for every HTTPS request.
- **UI that fetches profile data:** XGameUiShowPlayerProfileCardAsync.
- **Carriers, not sources:** XAsync and XTaskQueue (and XThreadAssertNotTimeSensitive) make no traffic themselves. They
  carry all of libHttpClient's HTTP and websocket work (HC_CALL::PerformAsync, WinHttpConnection, XCurlMulti) and XSAPI's
  calls. Presence, social ("People"), multiplayer activity and invites go out through XSAPI over libHttpClient, not
  through these thunks. For example, 14019FCB0 calls 1406D4DB0 with "People", and 1401A2790 calls 1406D7E10.
- **Local only, but they choose a backend:** XSystemGetXboxLiveSandboxId (bdHTTPAuthService::getEnvironment picks the
  RETAIL / Certification / Development Demonware environment from it) and XGameGetXboxTitleId.

## Required to keep running

**No path from sign-in, the licence or connectivity quits the process.** Every failure ends in a LUI popup or in
online features staying disabled. The two `MessageBoxW` calls at start-up are the hardest stops, and their return value
is ignored. Details:

1. **Runtime start-up: GDK_Init 1401A1930, called from Com_Init 140461550.**
   - `XGameRuntimeInitialize` (1406AF4BC) failing → if hr is 0x89240101 or 0x89240102,
     `MessageBoxW "Game Runtime is not installed on this system or needs updating."` → return 0.
     The local loader and missing-export check both produce 0x89240101.
   - `XGameGetXboxTitleId` (1406AF32C) failing → `MessageBoxW "Title ID not found in MicrosoftGameConfig.mgc file."`
     → return 0. Outside its package the exe has no MicrosoftGame.config.
   - Com_Init ignores the return value and keeps going. But all GDK set-up is then skipped: gamesave, users, presence,
     store and session queues are never created, so there is no sign-in, no licence and no online.
   - 1406AEC18 calls `DebugBreak()` when runtime initialisation fails and KUSER_SHARED_DATA+0x2D4 & 3 == 3 (a kernel
     debugger is present). Keep this in mind when testing under a debugger.
   - Without initialisation, every later QueryApi retries 1406AEC18(1). When only the
     legacy initializer is available, this reports `XErrorReport(0x89240100,
     "XGameRuntimeInitialize must be called before making this call.")`. With Ex
     available it instead attempts implicit initialization.
2. **Sign-in: GDK frame 1401A1760, called each frame from Live_Frame 14054B4B0.**
   - Sign-in starts only in the main menu (`FUN_140222950()`), once, when 1401A7EA0 says no signed-in user
     (user+0x80 XUserState != 0, or an add is in progress).
   - Step 1: 1401A8000 calls `XUserAddAsync(AddDefaultUserSilently=1)`. Its completion 1401A9010 calls XUserAddResult,
     then XUserGetId.
   - Step 2: if GetId fails, 1401A9200 calls `XUserAddAsync(AddDefaultUserAllowingUI=4)`. If that also fails, 1401A90C0
     calls `XUserResolveIssueWithUiAsync("https://www.xboxlive.com")`.
   - When all of this fails, the user simply stays signed out. Sign-in is retried only through LUI (14054CF70 →
     1401A1AF0).
   - On success, 1401A8960 makes these calls in order and **returns at the first failure**:
     1. XblContextCreateHandle (1406D9FD0)
     2. a second XSAPI context call (1406DA190, not identified)
     3. XUserGetGamertag
     4. XUserGetState
     5. XUserGetAgeGroup
     6. XUserGetIsGuest
     7. 15 × XUserCheckPrivilege
     8. gamer picture
     9. XUserRegisterForChangeEvent
     10. XNetworkingRegisterConnectivityHintChanged
     11. 1401A57C0: XStoreCreateContext, then the licence check, package enumeration and DLC licences.

     **Any failure in this chain means no licence check, so no online.**
   - Sign-out (change event SignedOut, handled in 1401A7440): the game closes saves, the user and the XblContext.
     In a match it runs `disconnect`; in the main menu it opens the `not_signed_in_request` popup.
3. **Licence: decided in 1401A5550 (completion of XStoreQueryGameLicenseAsync, started by 1401A5930).**
   - Licence state is kept in globals:

     | Global | Meaning |
     |---|---|
     | DAT_142E670B8 | query state: 0 none, 2 error, 3 done |
     | DAT_142E670B0 | licensed |
     | DAT_142E670B3 | store-mismatch popup pending |

   - **Store-mismatch check, before the licence:** if `XUserIsStoreUser(user)` is false, or no XblContext exists, or
     the dvar `fake_gdk_store_mismatch` is set (1401A7F20), the result is ignored. The game then opens
     `error_popmenu_store_mismatch_user` (from 1401A53E0).
   - The licence query fails to start, the result fails, or the async fails (1401A54B0) → state 2 and popup
     `error_popmenu_license` with @XBOXLIVE_LICENSEERROR*_GDK.
   - `!license.isActive` (+0x12), or `isTrial` (+0x15) with `!isTrialOwnedByThisUser` (+0x13) or
     `trialTimeRemainingInSeconds == 0` (+0x18) → popup `error_popmenu_license` with @XBOXLIVE_INVALIDLICENSE*_GDK,
     state 3, licensed 0.
   - Otherwise licensed = 1, state 3, and the add-on query starts.
   - **Where it takes effect:** 1401A1760 initialises the online systems only when `1401A5740() == 4` (state 3) and
     `1401A61A0()` (licensed). The online init is 1401A10E0, 1401A1190, ... 1405EC320 ... 1401A28C0
     (XGameInviteRegisterForEvent). Until then it calls 1405F3B10(0) and skips them.
   - The online-play checks 14054B1B0/14054B290 return reason 0xC (and false) when the user is not signed in or not
     licensed.
   - LUI `CheckGameLicense` (140245440) re-runs the check.
   - **Not established here:** whether the `error_popmenu_license` buttons quit the game. That is Lua in the
     fastfiles, not exe code. No quit, exit or Com_Error call was found on these paths in the exe.

## Unresolved or weak

- **1406B14FC XThreadAssertNotTimeSensitive (0.6).** The no-argument void core slot 0xe8 that 26 thunks call first.
  The name comes from behaviour, not from a string.
- **XGameUI slots 0x38/0x40 (0.7/0.6).** ShowPlayerProfileCard fits (async, user, XUID) and the friends-list callers.
  ShowErrorDialogAsync has the same arity.
- **XPackage 0x128/0x130 (0.7).** MountWithUiAsync/Result by shape and use; an older `XPackageMountAsync`-style pair
  cannot be ruled out. Register/UnregisterPackageInstalled (0x140/0xb0, 0.7) are inferred from the token pattern.
- **XUserIsStoreUser (0.75).** Inferred from the store-mismatch logic, not from a string.
- **XStoreShowProductPageUIAsync (0.7).** Its fallback URI is the product page.
- **XGameSaveSubmitUpdateResult, XGameUiShowPlayerProfileCardResult.** No callers; named only from slot order.
- **Names of the game-side wrappers.** The labels in the callers column (GDK_Init, licence result, ...) are
  descriptive, not original names, so they are not in records/names.tsv.
- **Network column.** "yes" means the call can reach a service through Gaming Services. Whether it actually does
  (cached tokens, cached licence) depends on the runtime.

## Thunk table

Callers are the full list from callgraph.tsv. Labels: (TaskManager) game 14045Fxxx, (XSAPI) 1406D-1406F, (libHttpClient)
1407B-1407F, (GDK thunk) another thunk.

| thunk | interface | slot | GDK function | conf | evidence | callers | network? | purpose |
|---|---|---|---|---|---|---|---|---|
| 1406AEEF4 | XAsync/XTaskQueue/XThread (core) | 0x38 | XAsyncBegin | 0.9 | 5 args (async,context,identity,identityName,provider); callers pass identity names "xbox::httpclient::CurlMulti::CleanupAsync", "HC_CALL::PerformAsync", "xbox::services::GlobalState::CleanupAsync" | 1406E0920 (XSAPI); 1406E7520 (XSAPI); 1407B42E0 (libHttpClient); 1407B52C0 (libHttpClient); 1407B5740 (libHttpClient); 1407B5CC0 (libHttpClient); 1407B8820 (libHttpClient); 1407B8900 (libHttpClient); 1407BAA80 (libHttpClient); 1407BC7C0 (libHttpClient); 1407BCEF0 (libHttpClient); 1407C2C80 (libHttpClient); 1407C69E0 (libHttpClient); 1407C74E0 (libHttpClient) | no | libHttpClient/XSAPI start async providers (HTTP perform, websocket, cleanup) |
| 1406AEF98 | XAsync/XTaskQueue/XThread (core) | 0x28 | XAsyncCancel | 0.8 | void(XAsyncBlock*); slot 0x28 between GetResultSize and Begin as in XAsync.h; game TaskManager cancel paths and libHttpClient cleanup | 14045EF30 (TaskManager); 14045EF80 (TaskManager); 14045F010 (TaskManager); 14045F0B0 (TaskManager); 14045F150 (TaskManager); 14045F1C0 (TaskManager); 14045F1F0 (TaskManager); 14045F2D0 (TaskManager); 14045F4F0 (TaskManager); 1407B5340 (libHttpClient); 1407B5820 (libHttpClient) | no | cancel pending async tasks (game TaskManager 14045Fxxx, libHttpClient cleanup) |
| 1406AEFF0 | XAsync/XTaskQueue/XThread (core) | 0x50 | XAsyncComplete | 0.85 | void(async, HRESULT, requiredBufferSize); 39 callers, all provider completion points (WinHttp/Curl request complete, cleanup complete) | 1406D2360 (XSAPI); 1406D3C80 (XSAPI); 1406D3DA0 (XSAPI); 1406D7450 (XSAPI); 1406D9150 (XSAPI); 1406D92D0 (XSAPI); 1406DFF20 (XSAPI); 1406E0FC0 (XSAPI); 1407B3A80 (libHttpClient); 1407B5340 (libHttpClient); 1407B59D0 (libHttpClient); 1407B5A00 (libHttpClient); 1407B5F30 (libHttpClient); 1407B85D0 (libHttpClient); 1407B8900 (libHttpClient); 1407B8A20 (libHttpClient); 1407B8BD0 (libHttpClient); 1407BADE0 (libHttpClient); 1407BC7A0 (libHttpClient); 1407BCF30 (libHttpClient); 1407BD4D0 (libHttpClient); 1407C1240 (libHttpClient); 1407C1420 (libHttpClient); 1407C2CF0 (libHttpClient); 1407C6690 (libHttpClient); 1407C73C0 (libHttpClient); 1407C7A70 (libHttpClient); 1407C7FC0 (libHttpClient); 1407C81B0 (libHttpClient); 1407C8450 (libHttpClient); 1407C8720 (libHttpClient); 1407C89D0 (libHttpClient); 1407C8A60 (libHttpClient); 1407C9AB0 (libHttpClient); 1407C9D50 (libHttpClient); 1407F35C0 (libHttpClient); 1407F36D0 (libHttpClient); 1407F3780 (libHttpClient); 1407F3840 (libHttpClient) | no | libHttpClient/XSAPI complete async operations |
| 1406AF06C | XAsync/XTaskQueue/XThread (core) | 0x58 | XAsyncGetResult | 0.85 | 5 args (async, identity, bufferSize, buffer, bufferUsed); slot 0x58 after Complete as in XAsyncProvider.h | 1406D2AA0 (XSAPI); 1406D4D30 (XSAPI); 1406D7F80 (XSAPI); 1406D9C70 (XSAPI); 1406D9EF0 (XSAPI); 1407B2180 (libHttpClient); 1407B21B0 (libHttpClient) | no | XSAPI/libHttpClient fetch typed async results |
| 1406AF110 | XAsync/XTaskQueue/XThread (core) | 0x20 | XAsyncGetResultSize | 0.85 | (async, size_t*); 1401A1480 calls GetStatus -> this -> XGameSaveReadBlobDataResult with the size | 1401A1480 (gamesave read done); 1406D2B30 (XSAPI); 1406D4D70 (XSAPI); 1406D7FF0 (XSAPI); 1406D9D90 (XSAPI); 1406D9F30 (XSAPI) | no | size of async result buffers (game saves, XSAPI) |
| 1406AF188 | XAsync/XTaskQueue/XThread (core) | 0x18 | XAsyncGetStatus | 0.95 | 140762430 logs "XAsyncGetStatus: unexpected result 0x%08X"; args (async, bool wait) | 1401A1480 (gamesave read done); 1401A1A30 (GDK_Shutdown); 1401A4C70 (task cancel cb); 1401A54B0 (licence query failed); 1401A56C0 (task cancel cb); 14045F4F0 (TaskManager); 1406E0FC0 (XSAPI); 140762430 (DW GDK task: status); 1407B39C0 (libHttpClient); 1407B59D0 (libHttpClient); 1407B5A00 (libHttpClient); 1407B8BD0 (libHttpClient); 1407BF9E0 (libHttpClient) | no | poll/wait on async blocks (GDK task manager, licence, shutdown waits) |
| 1406AF200 | XAsync/XTaskQueue/XThread (core) | 0x48 | XAsyncSchedule | 0.9 | (async, uint32 delayMs); callers log "Unable to schedule NetworkState::CleanupAsyncProvider" | 1406DFDB0 (XSAPI); 1406E6680 (XSAPI); 1407B39C0 (libHttpClient); 1407B3A80 (libHttpClient); 1407B5340 (libHttpClient); 1407B5820 (libHttpClient); 1407B5BE0 (libHttpClient); 1407B5F30 (libHttpClient); 1407C2CF0 (libHttpClient); 1407C2DB0 (libHttpClient); 1407C30C0 (libHttpClient) | no | libHttpClient schedules provider work |
| 1406AF274 | XGameEvent | 0x18 | XGameEventWrite | 0.85 | 6 args (user, scid, playSessionId, name, dimensions, measurements) in XSAPI events 1407179B0 after IsFeatureAvailable(20); game writes "AchievementNUnlocked" events via 14019F3D0 | 1407179B0 (XSAPI events write) | yes | achievement / stat events to Xbox Live |
| 1406AF32C | XGame | 0x18 | XGameGetXboxTitleId | 0.95 | 1401A1930 shows "Title ID not found in MicrosoftGameConfig.mgc file." when it fails; result formatted into the SCID ...66cdd1f0 | 1401A0AB0 (friends presence title check); 1401A0C80 (friends presence status); 1401A1930 (GDK_Init); 1406FD380 (XSAPI init) | no | title id (friends "playing this game" check, XSAPI init) |
| 1406AF39C | XGameInvite | 0x18 | XGameInviteRegisterForEvent | 0.85 | (queue, context=user, callback 1401A2C70, token*); callback parses "connectionString=" from the invite URI | 1401A28C0 (invite register) | no | receive game invites / joins |
| 1406AF43C | XGameInvite | 0x20 | XGameInviteUnregisterForEvent | 0.85 | (token, bool wait) in 1401A28C0/1401A2940 | 1401A28C0 (invite register); 1401A2940 (session shutdown) | no | unregister |
| 1406AF4C4 | XGameRuntimeFeature | 0x18 | XGameRuntimeIsFeatureAvailable | 0.85 | bool(uint32 feature); bdHTTPWorker passes 10 (XNetworking) before XNetworking calls, XSAPI events passes 20 (XGameEvent) before XGameEventWrite | 1407179B0 (XSAPI events write); 1407BFD20 (libHttpClient); 1407CCBF0 (bdHTTPWorker ctor); 1407CF690 (bdHTTPWorker initializeWinHTTP) | no | feature probe |
| 1406AF5C4 | XGameSave | 0x88 | XGameSaveCloseContainer | 0.85 | void(container) closing DAT_142E62FC8 in 1401A1620 | 1401A1620 (gamesave close) | no | close container |
| 1406AF628 | XGameSave | 0x30 | XGameSaveCloseProvider | 0.85 | void(provider) closing DAT_142E62FC0 in 1401A1620 | 1401A1620 (gamesave close) | no | close provider |
| 1406AF68C | XGameSave | 0xc0 | XGameSaveCloseUpdate | 0.85 | void(update) at the end of 1401A1670 | 1401A1670 (gamesave write) | no | end save write |
| 1406AF6F0 | XGameSave | 0x80 | XGameSaveCreateContainer | 0.9 | (provider, "Gamerprofile_gdk", container*) in 1401A1230 | 1401A1230 (gamesave provider ready) | no | open profile container |
| 1406AF784 | XGameSave | 0xb8 | XGameSaveCreateUpdate | 0.85 | (container, "Gamerprofile_gdk", update*) in 1401A1670 | 1401A1670 (gamesave write) | no | begin save write |
| 1406AF818 | XGameSave | 0x20 | XGameSaveInitializeProviderAsync | 0.9 | (user, scid "00000000-0000-0000-0000-000066cdd1f0", bool syncOnDemand=1, async) in 1401A15A0 | 1401A15A0 (gamesave open provider) | yes | open cloud-synced save provider (Connected Storage) |
| 1406AF8B4 | XGameSave | 0x28 | XGameSaveInitializeProviderResult | 0.9 | (async, provider*) in completion 1401A1230 | 1401A1230 (gamesave provider ready) | yes | provider handle |
| 1406AF930 | XGameSave | 0xa8 | XGameSaveReadBlobDataAsync | 0.85 | (container, blobNames[], uint32 count=1, async) in 1401A1390 | 1401A1390 (gamesave read) | yes | read profile blob (may sync from cloud) |
| 1406AF9D0 | XGameSave | 0xb0 | XGameSaveReadBlobDataResult | 0.9 | (async, size, blobs*, count*) after XAsyncGetResultSize in 1401A1480 | 1401A1480 (gamesave read done) | no | profile blob data |
| 1406AFA70 | XGameSave | 0xc8 | XGameSaveSubmitBlobWrite | 0.85 | (update, blobName, data, size) in 1401A1670 before the submit | 1401A1670 (gamesave write) | no | stage profile blob |
| 1406AFB14 | XGameSave | 0xe0 | XGameSaveSubmitUpdateAsync | 0.85 | (update, async) in 1401A1670 | 1401A1670 (gamesave write) | yes | commit save (synced to cloud) |
| 1406AFB90 | XGameSave | 0xe8 | XGameSaveSubmitUpdateResult | 0.6 | (async), no direct callers (completion only checks status); slot follows SubmitUpdateAsync | (none) | no | unused |
| 1406AFC00 | XGameUI | 0x38 | XGameUiShowPlayerProfileCardAsync | 0.7 | (async, requestingUser, targetXuid) from friends UI (1405EBA70, 1405EC610 pass a user handle and a friend entry XUID) | 14019FA40 (GDK_ShowProfileCard); 1401A8860 (profile card) | yes | show profile card |
| 1406AFC88 | XGameUI | 0x40 | XGameUiShowPlayerProfileCardResult | 0.6 | (async), no callers; slot after the Async | (none) | yes | unused |
| 1406AFCF4 | XNetworking | 0x78 | XNetworkingGetConnectivityHint | 0.95 | 1407CCBF0 logs "XNetworkingGetConnectivityHint() failed"; 1407BFFC0 "Unable to get NetworkConnectivityHint" | 1407BFFC0 (libHttpClient); 1407CCBF0 (bdHTTPWorker ctor) | no | is the network up |
| 1406AFD60 | XNetworking | 0x40 | XNetworkingQuerySecurityInformationForUrlAsync | 0.8 | (url, async) in libHttpClient 1407BF9E0; slot 0x40 precedes the anchored Utf16 trio at 0x58/0x60/0x68 | 1407BF9E0 (libHttpClient) | yes | TLS/certificate-pinning info for a URL (libHttpClient) |
| 1406AFDDC | XNetworking | 0x50 | XNetworkingQuerySecurityInformationForUrlAsyncResult | 0.8 | 5 args (async, size, buffer, ptr*, used*) in 1407BF9E0 | 1407BF9E0 (libHttpClient) | yes | security info |
| 1406AFE84 | XNetworking | 0x48 | XNetworkingQuerySecurityInformationForUrlAsyncResultSize | 0.8 | (async, size_t*) in 1407BF9E0 | 1407BF9E0 (libHttpClient) | yes | security info size |
| 1406AFF00 | XNetworking | 0x58 | XNetworkingQuerySecurityInformationForUrlUtf16Async | 0.95 | 1407CDA50 logs "XNetworkingQuerySecurityInformationForUrlUtf16Async() Failed" | 1407CDA50 (bdHTTPWorker QuerySecurityInformation) | yes | security info for Demonware URLs (bdHTTPWorker) |
| 1406AFF7C | XNetworking | 0x68 | XNetworkingQuerySecurityInformationForUrlUtf16AsyncResult | 0.95 | 1407CDB90 logs "...Utf16AsyncResult() Failed" | 1407CDB90 (bdHTTPWorker QuerySecurityInformationCallback) | yes | security info |
| 1406B0024 | XNetworking | 0x60 | XNetworkingQuerySecurityInformationForUrlUtf16AsyncResultSize | 0.95 | 1407CDB90 logs "...Utf16AsyncResultSize() Failed" | 1407CDB90 (bdHTTPWorker QuerySecurityInformationCallback) | yes | security info size |
| 1406B00A0 | XNetworking | 0x80 | XNetworkingRegisterConnectivityHintChanged | 0.95 | 1407CCBF0 logs "XNetworkingRegisterConnectivityHintChanged() failed"; (queue, context, callback, token*) | 1401A8960 (user signed-in setup); 1407BFD20 (libHttpClient); 1407CCBF0 (bdHTTPWorker ctor) | no | connectivity change notifications (game 1401A8960, bdHTTPWorker, libHttpClient) |
| 1406B0140 | XNetworking | 0x88 | XNetworkingUnregisterConnectivityHintChanged | 0.85 | (token, bool wait), the token from the Register call (1401A7440, 1401A88C0, 1407BE380) | 1401A7440 (user change handler); 1401A88C0 (users shutdown); 1407BE380 (libHttpClient) | no | unregister |
| 1406B01C8 | XNetworking | 0x70 | XNetworkingVerifyServerCertificate | 0.8 | (requestHandle, securityInfo) from WinHTTP SECURE_FAILURE/status callbacks (1407C8A60, bdHTTP 1407CE180) | 1407C8A60 (libHttpClient); 1407CE180 (bdHTTPWorker WinHttpStatusCallback) | yes | certificate pinning check on WinHTTP requests |
| 1406B0248 | XPackage | 0xd0 | XPackageCloseMountHandle | 0.8 | void(mount) in 1401A5850/1401A6110 | 1401A5850 (store shutdown); 1401A6110 (store reset) | no | unmount DLC |
| 1406B02AC | XPackage | 0x138 | XPackageEnumeratePackages | 0.8 | (kind=1 Content, scope=0, context, callback 1401A4D20); callback reads XPackageDetails packageIdentifier/displayName/storeId and skips installing packages (+0x38) | 1401A57C0 (store init) | no | list installed DLC packages |
| 1406B0350 | XPackage | 0xc8 | XPackageGetMountPath | 0.85 | (mount, 0x100, path) in 1401A4FB0; path then registered for map packs ("9PNWS8PBZ21B") | 1401A4FB0 (DLC mount done) | no | DLC path |
| 1406B03E4 | XPackage | 0x58 | XPackageGetUserLocale | 0.85 | (size=0x55 = LOCALE_NAME_MAX_LENGTH, buffer) in 1401A18D0, result matched against a table starting "en-us" | 1401A18D0 (user locale) | no | pick UI language |
| 1406B0464 | XPackage | 0x128 | XPackageMountWithUiAsync | 0.7 | (packageIdentifier, async) in 1401A4EB0, completion reads a mount handle; slot 0x128 next to its Result | 1401A4EB0 (DLC mount) | no | mount DLC package |
| 1406B04E0 | XPackage | 0x130 | XPackageMountWithUiResult | 0.7 | (async, XPackageMountHandle*) in 1401A4FB0 | 1401A4FB0 (DLC mount done) | no | DLC mount handle |
| 1406B055C | XPackage | 0x140 | XPackageRegisterPackageInstalled | 0.7 | (queue, context, callback, token*) in 1401A57C0; token unregistered by 1406B05FC | 1401A57C0 (store init) | no | new DLC installed notification |
| 1406B05FC | XPackage | 0xb0 | XPackageUnregisterPackageInstalled | 0.7 | (token, bool wait) in 1401A5850/1401A6110 | 1401A5850 (store shutdown); 1401A6110 (store reset) | no | unregister |
| 1406B0684 | XStore | 0xa0 | XStoreAcquireLicenseForPackageAsync | 0.85 | (ctx, packageIdentifier, async) from the package enumeration callback 1401A4D20 | 1401A4D20 (package enum cb) | yes | DLC package licence |
| 1406B0710 | XStore | 0xa8 | XStoreAcquireLicenseForPackageResult | 0.85 | (async, XStoreLicenseHandle*) in 1401A4CA0 | 1401A4CA0 (DLC licence done) | yes | DLC licence handle |
| 1406B078C | XStore | 0x20 | XStoreCloseContextHandle | 0.9 | void(ctx) clearing DAT_142E66970 in 1401A5850/1401A6110 | 1401A5850 (store shutdown); 1401A6110 (store reset) | no | close store context |
| 1406B07E8 | XStore | 0xb8 | XStoreCloseLicenseHandle | 0.85 | void(license) in 1401A5850/1401A6110 | 1401A5850 (store shutdown); 1401A6110 (store reset) | no | close DLC licence |
| 1406B0848 | XStore | 0x98 | XStoreCloseProductsQueryHandle | 0.85 | void(queryHandle) in 1401A56F0/1401A58E0/1401A6340 | 1401A56F0 (add-on query done); 1401A58E0 (add-on next page); 1401A6340 (add-on enumerate) | no | close query |
| 1406B08A8 | XStore | 0x18 | XStoreCreateContext | 0.9 | (user, XStoreContextHandle*) into DAT_142E66970 in 1401A57C0, first function of the interface (slot 0x18) | 1401A57C0 (store init) | no | store context for licence/DLC |
| 1406B0928 | XStore | 0x78 | XStoreEnumerateProductsQuery | 0.85 | (queryHandle, context, callback 1401A50B0) in 1401A6340 | 1401A6340 (add-on enumerate) | no | walk add-on results |
| 1406B09B0 | XStore | 0xb0 | XStoreLicenseIsValid | 0.85 | bool(license) in 1401A4CA0; valid -> mount the DLC package | 1401A4CA0 (DLC licence done) | no | DLC licence valid? |
| 1406B0A20 | XStore | 0x80 | XStoreProductsQueryHasMorePages | 0.85 | bool(queryHandle) in 1401A6340 | 1401A6340 (add-on enumerate) | no | paging |
| 1406B0A90 | XStore | 0x88 | XStoreProductsQueryNextPageAsync | 0.85 | (queryHandle, async) in 1401A6340 | 1401A6340 (add-on enumerate) | yes | next page |
| 1406B0B0C | XStore | 0x90 | XStoreProductsQueryNextPageResult | 0.85 | (async, queryHandle*) in 1401A58E0 | 1401A58E0 (add-on next page) | yes | next page result |
| 1406B0B88 | XStore | 0x48 | XStoreQueryAssociatedProductsAsync | 0.85 | (ctx, kinds=6, maxItems=25, async) after a valid licence in 1401A5550 | 1401A5550 (licence result) | yes | DLC / add-on catalogue |
| 1406B0C24 | XStore | 0x50 | XStoreQueryAssociatedProductsResult | 0.85 | (async, queryHandle*) in 1401A56F0 | 1401A56F0 (add-on query done) | yes | add-on query handle |
| 1406B0CA0 | XStore | 0xe0 | XStoreQueryGameLicenseAsync | 0.9 | (ctx, async) in 1401A5930, the licence check started by LUI CheckGameLicense (140245440); failures show error_popmenu_license | 1401A5930 (licence query start) | yes | game licence check |
| 1406B0D1C | XStore | 0xe8 | XStoreQueryGameLicenseResult | 0.9 | (async, XStoreGameLicense*) in 1401A5550; fields read at +0x12 isActive, +0x13 isTrialOwnedByThisUser, +0x15 isTrial, +0x18 trialTimeRemainingInSeconds | 1401A5550 (licence result) | yes | licence result |
| 1406B0D98 | XStore | 0x258 | XStoreShowProductPageUIAsync | 0.7 | slot 0x258 (late addition), 3 args (ctx, storeId, async) in 1401A5B10, whose fallback opens "ms-windows-store://pdp/?productId=" | 1401A5B10 (open store page) | yes | open store page for an add-on |
| 1406B0F24 | XSystem | 0x20 | XSystemGetXboxLiveSandboxId | 0.85 | (size, buffer, used) in bdHTTPAuthService::getEnvironment (140749EF0) choosing "RETAIL"/Certification/Development, and XSAPI init 1406FD380 | 1406FD380 (XSAPI init); 140749EF0 (bdHTTPAuthService::getEnvironment) | no | choose Demonware environment from sandbox |
| 1406B0FB4 | XAsync/XTaskQueue/XThread (core) | 0x88 | XTaskQueueCloseHandle | 0.85 | void(queue); closes queues created by XTaskQueueCreate/Duplicate (1401A1530, 1401A2940, 1401A88C0) | 1401A1530 (gamesave shutdown); 1401A1CD0 (presence shutdown); 1401A2940 (session shutdown); 1401A88C0 (users shutdown); 1406E6030 (XSAPI); 1406E62C0 (XSAPI); 1406E6420 (XSAPI); 1406E6430 (XSAPI); 1406E6970 (XSAPI); 1406E6D40 (XSAPI); 1406E6EC0 (XSAPI); 14070E9A0; 1407B51D0 (libHttpClient); 1407B5740 (libHttpClient); 1407B5820 (libHttpClient); 1407B85D0 (libHttpClient); 1407B8820 (libHttpClient); 1407BAA80 (libHttpClient); 1407BAC50 (libHttpClient); 1407BCE10 (libHttpClient); 1407BE380 (libHttpClient); 1407C2920 (libHttpClient); 1407C29B0 (libHttpClient); 1407CCFF0 (bdHTTPWorker dtor) | no | close task queues |
| 1406B1010 | XAsync/XTaskQueue/XThread (core) | 0x60 | XTaskQueueCreate | 0.95 | 1407CCBF0 logs "bdHTTPWorker(WinHTTP): XTaskQueueCreate() failed"; (uint32 workMode, uint32 completionMode, XTaskQueueHandle*) | 14019FA40 (GDK_ShowProfileCard); 14019FCB0 (XSAPI social "People" request); 1401A0420 (GDK people task); 1401A12D0 (gamesave init); 1401A1A30 (GDK_Shutdown); 1401A1C70 (presence init); 1401A2510 (session init); 1401A5B10 (open store page); 1401A85F0 (users init); 1407BFD20 (libHttpClient); 1407CCBF0 (bdHTTPWorker ctor) | no | create task queues: GDK tasks, users, gamesave, presence, session, store, bdHTTPWorker |
| 1406B1098 | XAsync/XTaskQueue/XThread (core) | 0x68 | XTaskQueueCreateComposite | 0.85 | (workPort, completionPort, queue*) called with the same port twice right after XTaskQueueGetPort (1406E6030, XCurlMulti::Initialize 1407C2F30) | 1406E6030 (XSAPI); 1406E6D40 (XSAPI); 1406E6EC0 (XSAPI); 1407B5820 (libHttpClient); 1407B5E20 (libHttpClient); 1407B85D0 (libHttpClient); 1407BAC50 (libHttpClient); 1407BCF30 (libHttpClient); 1407C2F30 (libHttpClient) | no | libHttpClient composite queues |
| 1406B1124 | XAsync/XTaskQueue/XThread (core) | 0x80 | XTaskQueueDispatch | 0.85 | returns bool; (queue, port=1 Completion, timeoutMs) called in a do/while until false on shutdown (1401A1530), once per frame on game queues | 1401A1320 (gamesave frame); 1401A1530 (gamesave shutdown); 1401A1CA0 (presence frame); 1401A2790 (session frame) | no | game dispatches completion callbacks each frame (gamesave 1401A1320, presence 1401A1CA0, session 1401A2790) |
| 1406B11AC | XAsync/XTaskQueue/XThread (core) | 0x78 | XTaskQueueDuplicateHandle | 0.85 | (queue, queue*), result later closed with XTaskQueueCloseHandle (1406E6030) | 1406E6030 (XSAPI); 1406E6260 (XSAPI); 1406E6290 (XSAPI); 1406E62C0 (XSAPI); 1406E6D40 (XSAPI); 1406E6EC0 (XSAPI) | no | libHttpClient keeps queue references |
| 1406B1224 | XAsync/XTaskQueue/XThread (core) | 0xc8 | XTaskQueueGetCurrentProcessTaskQueue | 0.85 | bool(XTaskQueueHandle*); fallback when no queue given, error 0x800701AB otherwise (1406E0A30, 1406E6030) | 1406E0A30 (XSAPI); 1406E6030 (XSAPI); 1406E6D40 (XSAPI); 1406E6EC0 (XSAPI) | no | libHttpClient default process queue |
| 1406B1294 | XAsync/XTaskQueue/XThread (core) | 0x70 | XTaskQueueGetPort | 0.85 | (queue, uint32 port=0 Work, XTaskQueuePortHandle*) feeding CreateComposite; CurlProvider::PerformAsync | 1406E6030 (XSAPI); 1406E6D40 (XSAPI); 1406E6EC0 (XSAPI); 1407B5820 (libHttpClient); 1407B5E20 (libHttpClient); 1407B85D0 (libHttpClient); 1407BAC50 (libHttpClient); 1407BCF30 (libHttpClient); 1407BD570 (libHttpClient) | no | libHttpClient get work port |
| 1406B1318 | XAsync/XTaskQueue/XThread (core) | 0x90 | XTaskQueueSubmitCallback | 0.85 | (queue, port=0, context, callback) from XCurlMulti::AddRequest (1407C2A40) | 1407C2A40 (libHttpClient) | no | libHttpClient XCurl scheduling (vehicle for HTTP) |
| 1406B13B4 | XAsync/XTaskQueue/XThread (core) | 0x98 | XTaskQueueSubmitDelayedCallback | 0.85 | (queue, port, delayMs, context, callback); used by HC_CALL retry ("Retry after %lld ms") and XCurlMulti::Perform | 1406E7050 (XSAPI); 1406E7320 (XSAPI); 1406E7640 (XSAPI); 1406E7740 (XSAPI); 1407B85D0 (libHttpClient); 1407B8BD0 (libHttpClient); 1407C30C0 (libHttpClient) | no | libHttpClient retry/poll timers |
| 1406B145C | XAsync/XTaskQueue/XThread (core) | 0xb0 | XTaskQueueTerminate | 0.8 | (queue, bool wait, context, callback); called before CloseHandle on every game queue at shutdown and in ~bdHTTPWorkerWinHTTPImpl | 1401A1530 (gamesave shutdown); 1401A2940 (session shutdown); 1406DFDB0 (XSAPI); 1406E6970 (XSAPI); 1406E7920 (XSAPI); 1407B85D0 (libHttpClient); 1407C2CF0 (libHttpClient); 1407CCFF0 (bdHTTPWorker dtor) | no | shut down queues |
| 1406B14FC | XAsync/XTaskQueue/XThread (core) | 0xe8 | XThreadAssertNotTimeSensitive | 0.6 | no args, void, same core interface; called at the top of 26 other thunks (Async/blocking APIs) the way the GDK guards APIs that are not safe on time-sensitive threads | 1406AEFF0 (GDK thunk); 1406AF274 (GDK thunk); 1406AF32C (GDK thunk); 1406AF39C (GDK thunk); 1406AF43C (GDK thunk); 1406AF5C4 (GDK thunk); 1406AF628 (GDK thunk); 1406AF68C (GDK thunk); 1406AF6F0 (GDK thunk); 1406AF784 (GDK thunk); 1406AFA70 (GDK thunk); 1406B0140 (GDK thunk); 1406B01C8 (GDK thunk); 1406B0248 (GDK thunk); 1406B02AC (GDK thunk); 1406B0350 (GDK thunk); 1406B03E4 (GDK thunk); 1406B05FC (GDK thunk); 1406B08A8 (GDK thunk); 1406B0F24 (GDK thunk); 1406B1010 (GDK thunk); 1406B1098 (GDK thunk); 1406B1224 (GDK thunk); 1406B145C (GDK thunk); 1406B1F78 (GDK thunk); 1406B2228 (GDK thunk) | no | GDK-internal guard inside other thunks |
| 1406B1550 | XUser | 0x38 | XUserAddAsync | 0.95 | 1407628B0 logs "XUserAddAsync: unexpected result"; (uint32 options, async): game passes 1 (AddDefaultUserSilently) in 1401A8000 and 4 (AddDefaultUserAllowingUI) in 1401A9200 | 1401A8000 (sign-in silent); 1401A9200 (sign-in with UI); 1407628B0 (DW GDK task: XUserAddAsync) | yes | sign-in: silent, then with UI; Demonware auth task also adds the user |
| 1406B15C8 | XUser | 0x40 | XUserAddResult | 0.95 | 140762600 logs "XUserAddResult: unexpected result"; (async, XUserHandle*) in the add completions 1401A9010/1401A90C0 | 1401A9010 (silent add done); 1401A90C0 (UI add done); 140762600 (DW GDK task: XUserAddResult) | yes | sign-in result |
| 1406B1644 | XUser | 0xa0 | XUserCheckPrivilege | 0.85 | 5 args (user, options, uint32 privilege, bool*, reason*); 1401A93A0 loops 15 XUserPrivilege ids (185..255, 254=Multiplayer); 0x89245102 (resolve issue required) branches to ResolveIssueWithUi | 1401A93A0 (privilege check) | no | privilege checks (multiplayer, chat, UGC, crossplay ...) |
| 1406B16F0 | XUser | 0x20 | XUserCloseHandle | 0.9 | void(user); game releases DAT_142E67158 on sign-out (1401A7440) and on failed add (1401A9010) | 1401A7440 (user change handler); 1401A88C0 (users shutdown); 1401A9010 (silent add done); 1406F5E50 (XSAPI User dtor); 1406F64F0 (XSAPI User::Copy); 1406F7900 (XSAPI User::WrapHandle); 14074A030 (bdHTTPAuthService::handleGdkAsyncTask) | no | release user handles |
| 1406B174C | XUser | 0x28 | XUserCompare | 0.85 | int32(user1,user2), compared ==0 to find the controller owning a user (1401A7D30) and in friends code | 1401A05B0 (friends/presence update); 1401A0AB0 (friends presence title check); 1401A7D30 (user->controller) | no | map user handles to controllers |
| 1406B17C8 | XUser | 0x18 | XUserDuplicateHandle | 0.9 | XSAPI 1406F64F0/1406F7900 log "Copying user failed: User failed to duplicate."; slot 0x18 = first XUser function | 1406F64F0 (XSAPI User::Copy); 1406F7900 (XSAPI User::WrapHandle) | no | XSAPI copies user handles |
| 1406B1844 | XUser | 0x98 | XUserGetAgeGroup | 0.7 | (user, enum*) writes user+0x84 in 1401A8960; slot order | 1401A8960 (user signed-in setup) | no | age group |
| 1406B18C0 | XUser | 0x80 | XUserGetGamerPictureAsync | 0.8 | (user, uint32 size, async) in 1401A8CD0, completion 1401A8DA0 calls ResultSize/Result | 1401A8CD0 (gamerpic request) | yes | download gamer picture |
| 1406B194C | XUser | 0x90 | XUserGetGamerPictureResult | 0.8 | (async, 0x40000, buffer, used*) in 1401A8DA0 | 1401A8DA0 (gamerpic done) | yes | gamer picture bytes |
| 1406B19EC | XUser | 0x88 | XUserGetGamerPictureResultSize | 0.8 | (async, size_t*) in 1401A8DA0 before the Result call | 1401A8DA0 (gamerpic done) | yes | gamer picture size |
| 1406B1A68 | XUser (v2) | 0x18 | XUserGetGamertag | 0.85 | separate XUser version IID; 5 args (user, component, size, buffer, used); XSAPI 1406F6850 logs "Getting Gamertag failed with HR:"; game passes component 0, size 0x61 | 1401A7440 (user change handler); 1401A8960 (user signed-in setup); 1406F6850 (XSAPI User::Gamertag) | no | gamertag for UI |
| 1406B1B10 | XUser | 0x58 | XUserGetId | 0.95 | XSAPI 1406F6FC0 logs "Failed to get User ID with HRESULT"; game treats failure as "not signed in" after XUserAddResult | 1401A9010 (silent add done); 1401A90C0 (UI add done); 1406F6FC0 (XSAPI User init) | no | XUID of signed-in user |
| 1406B1B8C | XUser | 0x68 | XUserGetIsGuest | 0.8 | (user, bool*) writes a byte flag at user+0x01 in 1401A8960; slot order | 1401A8960 (user signed-in setup) | no | guest flag |
| 1406B1C08 | XUser | 0x48 | XUserGetLocalId | 0.95 | XSAPI 1406F6FC0 logs "Failed to get User LocalID with HRESULT" | 1401A95E0 (user change cb); 1406F6FC0 (XSAPI User init) | no | local id; user-change callback 1401A95E0 matches the event local id |
| 1406B1C84 | XUser | 0x70 | XUserGetState | 0.85 | (user, XUserState*) writes user+0x80, which 1401A7EA0/1401A7DF0 test ==0 (SignedIn) | 1401A8960 (user signed-in setup) | no | signed-in state |
| 1406B1D00 | XUser | 0xb8 | XUserGetTokenAndSignatureAsync | 0.9 | 9 args (user, options, method, url, headerCount, headers, bodySize, body, async); 140762780 passes "POST", "https://auth3.prod.demonware.net", Content-Type application/json; XSAPI "User::GetTokenAndSignature" | 1406F6B00 (XSAPI User::GetTokenAndSignature); 140762780 (DW GDK task: token for auth3.prod.demonware.net) | yes | XSTS token+signature for Demonware auth and every Xbox Live HTTP call |
| 1406B1DE0 | XUser | 0xc8 | XUserGetTokenAndSignatureResult | 0.85 | (async, size, buffer, ptr*, used*) in 1406F60F0 and Demonware 140762500 (whose log string is a copy-paste "XUserAddResult") | 1406F60F0 (XSAPI token result); 140762500 (DW GDK task: token result) | yes | token result |
| 1406B1E8C | XUser | 0xc0 | XUserGetTokenAndSignatureResultSize | 0.85 | (async, size_t*) paired with Result in XSAPI 1406F60F0 | 1406F60F0 (XSAPI token result) | yes | token result size |
| 1406B1F08 | XUser | 0x150 | XUserIsStoreUser | 0.75 | bool(user) at slot 0x150 (late addition); 1401A7F20 returns it unless dvar "fake_gdk_store_mismatch"; false leads to "error_popmenu_store_mismatch_user" | 1401A7F20 (IsStoreUser check) | no | check the Xbox user is the Store account (licence prerequisite) |
| 1406B1F78 | XUser | 0x108 | XUserRegisterForChangeEvent | 0.85 | (queue, context, callback, token*) registering 1401A95E0, whose (context, XUserLocalId, event) shape matches XUserChangeEventCallback | 1401A8960 (user signed-in setup) | no | sign-out / gamertag / privilege change notifications |
| 1406B201C | XUser | 0xe8 | XUserResolveIssueWithUiAsync | 0.9 | (user, url, async); 1401A90C0 passes "https://www.xboxlive.com" after a failed add; 1401A93A0 passes NULL on 0x89245102 | 1401A90C0 (UI add done); 1401A93A0 (privilege check) | yes | sign-in / account issue resolution UI |
| 1406B20A8 | XUser | 0xf0 | XUserResolveIssueWithUiResult | 0.85 | (async) in completion 1401A8EF0 | 1401A8EF0 (resolve-issue UI done) | yes | resolve-issue result |
| 1406B2118 | XUser | 0xa8 | XUserResolvePrivilegeWithUiAsync | 0.85 | (user, options, privilege, async) in 1401A93A0 when a privilege is denied | 1401A93A0 (privilege check) | yes | resolve denied privilege via Xbox UI |
| 1406B21B8 | XUser | 0xb0 | XUserResolvePrivilegeWithUiResult | 0.8 | (async) in its completion 1401A8E40 | 1401A8E40 (privilege UI done) | yes | privilege UI result |
| 1406B2228 | XUser | 0x110 | XUserUnregisterForChangeEvent | 0.85 | (token, bool wait) on sign-out (1401A7440) and shutdown (1401A88C0) | 1401A7440 (user change handler); 1401A88C0 (users shutdown); 1406F7880 (XSAPI unregister change) | no | unregister |

## Runtime helpers outside the table

| VA | name | conf | evidence |
|---|---|---|---|
| 1406AEE34 | XGameRuntime_LoadLibrary (xgameruntime.lib internal) | 0.8 | LoadLibraryExA of xgameruntime.dll; called from 1406AEC18 (per brief) |
| 1406AEC18 | XGameRuntime_EnsureInitialized (xgameruntime.lib internal) | 0.85 | GetProcAddress QueryApiImpl/InitializeApiImpl(Ex)/XErrorReport/UninitializeApiImpl; InitializeApiImplEx(0x633600002711,0x633600000C6D,flags); DebugBreak on failure when a kernel debugger is flagged in KUSER_SHARED_DATA |
| 1406AEE74 | XGameRuntime_QueryApi (xgameruntime.lib internal) | 0.9 | QueryApiImpl(&familyIID,&versionIID,&api); maps REGDB_E_CLASSNOTREG to 0x89240107 "XGameRuntime is missing required dependencies" |
| 1406AF4BC | XGameRuntimeInitialize | 0.9 | tail-calls 1406AEC18(0); first call in GDK_Init 1401A1930 which shows "Game Runtime is not installed..." on 0x89240101/0x89240102 |
| 1406AF52C | XGameRuntimeUninitialize | 0.9 | calls UninitializeApiImpl, clears the resolved pointers and FreeLibrary; last call of GDK_Shutdown 1401A1A30 |

## Reconstructed runtime and account boundary

`src/_external/gdk/xgameruntime.cpp` reconstructs the three internal helpers,
public runtime initialization/cleanup, the thread guard, title ID and feature
queries, `XUserAddAsync`, and `XUserGetTokenAndSignatureAsync`.
`src/win32/gdk.cpp` reconstructs game startup 1401A1930. Its original name and
source path remain unknown; the descriptive file groups this game-side code.

The loader caches `xgameruntime.dll`, using `LoadLibraryExA` flag 0x800.
Initialization resolves five exports under an SRW lock and accepts either the
legacy initializer or its Ex variant. Missing required exports return
0x89240101, as does load failure. The older descriptive missing-export value
0x89240102 is not the value in this binary. Implicit initialization requires
Ex; an explicit call after implicit initialization runs the initializer again.
The Ex call forwards full 64-bit flags with bit 1 set. A negative result invokes
`DebugBreak` only when the original shared-user-data debugger bits are both set.

Interface lookup preserves provider HRESULTs except for 0x80040154, translated
to 0x89240107 with the repair diagnostic. A failed lookup can leave the output
unchanged. Successful thunks invoke their observed COM slot and release the
interface even if that method fails. The title query calls the thread guard
first but does not abort when that separate query fails. Token arguments use an
explicit lowered Win64 forwarding contract: the original copies stack qwords,
so this header does not assert a complete SDK source prototype.

Game startup handles runtime/title failures before initializing config, the
GDK task set, gamesave, users, events, store, presence and sessions in order.
The title string uses signed `_itoa` behavior even for a title ID above INT_MAX.

`tests/differential/test_gdk.py` contains 1,273 comparisons across these 11
functions. These include 56 cases that connect reconstructed startup, runtime
lookup and COM thunks; only OS imports, DLL exports and interface providers are
modeled. No DLL is loaded and no vendor connection is made by the tests.
Twelve deliberate source mutations were rejected: loader flags, Ex flags,
implicit initialization, HRESULT translation, public initialization mode,
cleanup admission, interface release, title-query success, feature fallback,
account-add options, token count forwarding and startup order.

P0007 overrides loading, initialization, interface lookup, cleanup and game
startup in `enhanced/`. Entry points return unavailable (HRESULT 0x89240100),
lookup clears a supplied output pointer, and game startup returns false without
config, title, tasks, services or error dialogs. Cleanup clears runtime fields
without calling SDK callbacks or OS imports, preserving the lock and padding.
This is for offline startup, not unloading an already running SDK: it does not
release preexisting vendor resources or coordinate live SDK threads.
All six individual override removals make `test_gdk_offline.py` fail. Its
tests reject runtime/SDK calls, exercise empty and poisoned cached state, verify
output clearing and preserved fields, and run inherited thunks through
the actual enhanced interface lookup.

The fifteen reconstructed thunks inherit the actual enhanced lookup guard, including
account addition, results, account-repair UI and token/signature requests. Other original thunks and original
call sites are not redirected by this source-linking step. Full executable
integration, all remaining SDK paths, and the custom dedicated server are pending.

## Account results and repair UI

`test_gdk_user.py` verifies ten further wrappers: `XUserAddResult`,
`XUserCheckPrivilege`, `XUserGetId`, `XUserGetState`, token/signature result and
result-size retrieval, issue-resolution UI start/result and privilege-resolution
UI start/result. Each retains the original XUser family/version pair and observed
vtable slot. Query success includes positive HRESULTs, and a successful interface
acquisition is released even when its method fails. Query failure leaves caller
outputs untouched and invokes neither method nor release.

The 540 comparisons include null outputs, full-width pointers and token buffer
sizes, truncation of options/privileges to the observed 32-bit ABI, provider
writes on method failure and 60 cases connected to the reconstructed runtime.
The tests model interface providers and OS calls; they do not obtain actual user
handles, credentials or tokens. These are forwarding-contract tests, not a claim
to implement the provider's internal validation or asynchronous behavior.

The enhanced tests run all ten through the actual P0007 lookup guard with empty
and poisoned cached state. They require HRESULT 0x89240100 and unchanged outputs,
without callbacks, UI, SDK entry or synthesized async completions. This extends
the existing override through faithful calls; no additional API-specific override
is needed. A future local identity/server implementation still needs its own
explicit account, task and credential contract.

Thirteen intentional mutations were rejected: changing query-success admission
in each of the ten wrappers, swapping options/privilege, truncating token buffer
size to 32 bits and omitting token-result interface release. Removing the shared
enhanced lookup override also makes the new account/result test fail.

## Frame and reporting drivers

The Store game frame 1401A1760 is now reconstructed in `src/win32/gdk.cpp`.
Original subsystem names remain unknown; callback declarations use observed
call-site widths. In particular, branch results inspect the entire low byte,
not just bit zero. The driver rereads the signed-in query, so callbacks can
change the result within a single frame. It preserves sign-in/online-ready
latching, conditional online initialization and the unconditional ordered task,
save, user, friend, event, store, presence and session pumps.

Separate reconstructions cover event-task pump 14019F390, presence pump
1401A1CA0 and cloud-save pump 1401A1320. Presence/save dispatch completion port 1
with timeout 0 before their game task manager. Save processing also requires a
signed-in result, a nonnull provider and a pending flag; its callbacks precede
clearing that flag. Queues are dispatched even when no save work is admitted.

`XGameEventWrite` first invokes the thread guard, then queries the event IID
BBFBDCC7-BFE7-409B-A5CA-EDF054960B4D as both family and version and forwards six
arguments through slot 3. Thread-guard query failure does not abort the separate
event query. A successful acquisition is released even on method failure.

`test_gdk_reporting.py` compares these five functions with the original in 360
cases, including changing callback results, noncanonical true bytes, callback
writes to scheduling fields, null event payloads, provider failures and four
frame cases with the three reconstructed child pumps connected. Providers and
OS calls are modeled. P0008 stops these source-linked reporting paths in the
enhanced build; `test_reporting_offline.py` rejects dependency calls and checks
that poisoned provider/queue pointers and event payloads are never accessed.
