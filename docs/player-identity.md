# Store multiplayer player identity and presence

Target is the pinned Store 4.0.9.0 multiplayer EXE in target.toml. Addresses
are preferred VAs. Function descriptions are descriptive identifications
from the generated disassembly, PE strings, imports, and RTTI. The pseudocode
covers the operations shown here and is not a complete rebuild.

## Xbox user and controller records

| Address | Observed behavior |
|---|---|
| 1401A9010, 1401A90C0 | Silent and interactive user-add completions call XUserAddResult at 1406B15C8, then XUserGetId at 1406B1B10. The successful path reaches 1401A8960. |
| 1401A8960 | Installs the user handle and XUID into the controller record, fills its gamertag via XUserGetGamertag at 1406B1A68 (component 0, buffer size 0x61), fetches the XUser state, and registers the user-change callback. |
| 1401A95E0 | Calls XUserGetLocalId at 1406B1C08, compares the result against the callback's local ID, then ORs the event bit into the pending mask at 1430D0808 for the matching user. |
| 1401A7440 | Processes user-change work. The gamertag refresh calls 1406B1A68 again. A cleanup path closes the user handle and clears the controller record. |
| 1401A7D30 | Compares the incoming XUser handle against controller handles via XUserCompare at 1406B174C. Writes the controller index and returns true on a match. |
| 1401A7DB0 / 1401A7DD0 | Returns the address of the gamertag buffer / reads the XUser handle. |
| 1401A7DF0 / 1401A7E10 | Reads the 32-bit XUser state / reads the 64-bit XUID. |
| 1401A7E30 / 1401A7E50 / 1401A7EA0 | Tests for a cached service context / scans the controller records for a set first byte / combines XUser state zero with a clear global flag at 142E670E8. These are distinct checks. |

The accessor calculations establish this partial controller layout:

```text
base = 0x142E670F0 + signed_controller_index * 0x269728
base + 0x02  char[0x61]   gamertag buffer
base + 0x68  pointer      XUser handle
base + 0x70  pointer      cached service context
base + 0x78  uint64       Xbox user ID
base + 0x80  uint32       XUser state
```

The platform-local ID used to route Xbox user-change callbacks is a different
value from the XUID obtained by XUserGetId. The game has a separate name
cache too. The original frame path calls the Xbox accessors at 14054B7BB and
14054B7D6, then writes controller zero's XUID at 149D59D58 and copies the
name into a 32-byte buffer at 149D59D34. The cache's controller stride is 0x68.
14054C0D0 returns the cached name address; 14054C1A0 copies it to a
caller-provided buffer.

## Multiplayer wire identity

```text
14054C360(controller) -> tail jump to 1401A7E10(controller)
140314050(controller) -> tail jump to 14054C0F0(controller)

14054C0F0(controller):
    id = 1401A7E10(controller)
    buffer = 0x149D59D60 + signed_controller_index * 0x68
    14046AE00(&id, buffer)
    return buffer

14046AE00(&id, buffer):
    format(buffer, 17, "%08x%08x", high32(id), low32(id))
```

The format literal is at 14085EB38. For example, 0x1122334455667788
becomes `1122334455667788`. The userinfo builder at 140463EC0 reads the
name cache and the formatted ID through 140314050. The connect builder at
140311570 calls 14054C0F0 again and sets the `xuid` info key using the
string at 140835C08.

The direct package already redirects the gamertag accessor, the numeric
XUID accessor and its thunk, and the text accessor to its local profile.
The profile uses a nonzero 64-bit ID and the same lowercase hex encoding.
The `direct_player` handler mirrors the display name and ID into the
engine caches and sets the `name` dvar. The legacy wire key `xuid` still
carries that local ID in a direct session. The field carries no proof of
ownership and provides no Xbox account, user handle, or presence state.

## Presence and GUIDs

| Address | Observed behavior |
|---|---|
| 1401A1C70 | Creates the Xbox presence task queue at 142E64C08 and initializes the task list at 142E63E00 with the label "GDK presence tasks." |
| 1401A1CA0 | Dispatches completion port 1 with timeout zero, then pumps the task list. The enhanced vendor guard disables this pump. |
| 1401A0420 / 1401A05B0 | Xbox People task / friends and presence update. The update uses XUserCompare to match the user handle. |
| 1401A0AB0 / 1401A0C80 | Friends title check and status processing. Both call XGameGetXboxTitleId at 1406AF32C. The status routine iterates 0x1A8-byte records and compares an entry's title ID and presence text before assigning a display state. |
| 1406DBEB0 | Calls CoCreateGuid on a 16-byte value and StringFromGUID2 into a wide-character buffer. The caller at 1407178E1 stores the result in the Xbox `EventsService` object at offset 0x40. The vtable at 1408B7318 resolves to `EventsService@events@services@xbox` through MSVC RTTI. |

The GUID traced here belongs to Xbox events. The join path above has a
separate 64-bit identity. The enhanced direct profile currently provides
local identity and LAN eligibility. Xbox friends and rich presence remain
vendor paths. A local presence implementation would need its own state
based on direct-session membership, with consumers traced separately from
the Xbox sign-in predicates.
