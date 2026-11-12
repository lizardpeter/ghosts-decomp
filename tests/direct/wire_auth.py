#!/usr/bin/env python3
"""Compile the exact enhanced keyed-MAC and replay code against published vectors."""
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = r"""
#include "wire_auth.h"
#include <assert.h>
int main() {
    unsigned char key[16];
    unsigned char message[64];
    for (unsigned i = 0; i < 16; ++i) key[i] = (unsigned char)i;
    for (unsigned i = 0; i < 64; ++i) message[i] = (unsigned char)i;
    const unsigned long long reference[] = {
        0x726fdb47dd0e0e31ULL, 0x74f839c593dc67fdULL,
        0x0d6c8009d9a94f5aULL, 0x85676696d7fb7e2dULL,
    };
    for (unsigned i = 0; i < 4; ++i)
        assert(Iw6WireAuth::Mac(key, message, i) == reference[i]);
    // Direction is authenticated but not transmitted as an unauthenticated
    // field: the sender/receiver role is determined by transport state.
    unsigned char scoped[5] = {0, 1, 2, 3, 'C'};
    const auto clientTag = Iw6WireAuth::MacDirectional(key, message, 4, 'C');
    assert(clientTag == Iw6WireAuth::Mac(key, scoped, 5));
    scoped[4] = 'S';
    const auto serverTag = Iw6WireAuth::MacDirectional(key, message, 4, 'S');
    assert(serverTag == Iw6WireAuth::Mac(key, scoped, 5));
    assert(clientTag != serverTag);
    assert(!Iw6WireAuth::MacDirectional(key, message, 4, 'X'));
    assert(!Iw6WireAuth::MacDirectional(key, message, 1279, 'C'));
    unsigned char tag[8] = {0x72,0x6f,0xdb,0x47,0xdd,0x0e,0x0e,0x31};
    assert(Iw6WireAuth::EqualTag(reference[0], tag));
    tag[7] ^= 1;
    assert(!Iw6WireAuth::EqualTag(reference[0], tag));
    unsigned char parsed[16] = {};
    assert(Iw6WireAuth::ParseHexKey("000102030405060708090a0b0c0d0e0f", parsed));
    for (unsigned i = 0; i < 16; ++i) assert(parsed[i] == key[i]);
    assert(!Iw6WireAuth::ParseHexKey("", parsed));
    assert(!Iw6WireAuth::ParseHexKey("00000000000000000000000000000000", parsed));
    assert(!Iw6WireAuth::ParseHexKey("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz", parsed));
    Iw6WireAuth::ReplayWindow state = {};
    assert(!Iw6WireAuth::Accept(state, 0));
    assert(Iw6WireAuth::Accept(state, 1));
    assert(!Iw6WireAuth::Accept(state, 1));
    assert(Iw6WireAuth::Accept(state, 3));
    assert(Iw6WireAuth::Accept(state, 2));
    assert(!Iw6WireAuth::Accept(state, 2));
    assert(Iw6WireAuth::Accept(state, 100));
    assert(!Iw6WireAuth::Accept(state, 1));
    return 0;
}
"""

def main():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        (folder / "vectors.cpp").write_text(PROGRAM)
        subprocess.run([
            "g++", "-std=c++17", "-Wall", "-Wextra", "-Werror",
            "-I" + str(ROOT / "enhanced" / "direct"),
            str(folder / "vectors.cpp"), "-o", str(folder / "vectors"),
        ], check=True)
        subprocess.run([str(folder / "vectors")], check=True)
    print("PASS: SipHash-2-4 reference vectors, constant-time tag check, key parser and replay window")

if __name__ == "__main__":
    main()
