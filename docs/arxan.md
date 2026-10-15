# Arxan on the Steam exes

Applies to the related Steam builds (`protection = "arxan"` in target.toml). The reference servers are not
protected. Whether the Store build is protected gets checked when it arrives.

## What it does on disk

- `.text` and `.interpr` are encrypted in the file. Every 64 KB block of `.text` has entropy 7.66 to 8.00, and
  normal x64 prologues are missing. `.rdata` (strings), `.pdata` (function table), imports and resources are
  readable.
- The entry point is Arxan's stub. It begins with `push rax ... push rdi; pushfq` with REX-padded pushes, and
  its body runs in `.reloc`, a 27 MB section of stub code and data. The real base relocations (0x34AE4 bytes) sit
  at its end. The exe has no ASLR flag, so the relocations are never applied.
- There are no TLS callbacks. Nothing runs before the entry stub.

## What the stub does at startup (observed in emulation)

It resolves `VirtualProtect` with LoadLibraryA/GetProcAddress, makes every section RWX, calls GetSystemInfo and
walks the image with VirtualQuery. It then decrypts `.text` and `.interpr` in place, plus about 11 KB of
`.rdata`, and jumps into the decrypted CRT entry. The first ordinary API call is `GetSystemTimeAsFileTime`
from `__security_init_cookie`. It made no `rdtsc` calls on the path taken.

## tools/unpack/arxan.py

The tool emulates the stub in Unicorn x64 and answers the five kernel32 calls with fixed values. It stops at
the first runtime API call and writes the original file with the changed sections replaced by emulated memory.
The certificate entry and checksum are cleared.

The run must be one uninterrupted `emu_start`. Slicing the run by wall-clock timeouts gave different results
on each run, and one run crashed inside the stub. Run in one piece, three runs produced identical output, so
`unpacked_sha256` is pinned and CI rejects any deviation. `rdtsc` is hooked to a fixed counter as a safeguard
anyway.

Steam MP: about 150 s, `.text` mean entropy 6.44 after decryption, 34,901 `.pdata` entries. 44 of
iw6x-client's 62 MP addresses are `.pdata` starts. The other 18 are leaf functions, which have no unwind
entry, and their code reads as genuine.

Not done yet: the original entry point is not identified (the CRT-entry pattern search found no match), so
the unpacked file's entry point is still the stub's. That doesn't matter for static analysis.
