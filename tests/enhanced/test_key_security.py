"""Regression tests for source-linked IW6 S17 key binding bounds.
Native Store EXE callers still need separately verified entry redirects.
"""
KEY = "?Key_StringToKeynum@@YAHPEBD@Z"
SET = "?Key_SetBinding@@YAXW4LocalClientNum_t@@HH@Z"
GET = "?Key_GetBinding@@YAHW4LocalClientNum_t@@H@Z"
DOWN = "?Key_IsDown@@YAHW4LocalClientNum_t@@H@Z"

def test_key_string_s17_rejects_signed_bytes_and_bad_hex(env):
    for raw, wanted in [(b"", -1), (b"A", 65), (b"0x41", 65),
                        (b"0x80", 128), (b"0xFF", 255),
                        (b"0xGG", -1), (b"0x4G", -1),
                        (b"\x80", -1), (b"\xff", -1)]:
        result, _, writes, _ = env.call(KEY, [raw], ret="int")
        assert result == wanted and not writes, (raw, result, writes)

def test_key_state_s17_rejects_negative_and_oversize_indices(env):
    for client, key in [(0, -128), (0, -2), (0, -1), (0, 256),
                        (0, 65535), (-1, 4), (1, 4)]:
        value, _, writes, _ = env.call(SET, [client, key, 9])
        assert value is None and not writes, (client, key, writes)
        for fn in (GET, DOWN):
            result, _, writes, _ = env.call(fn, [client, key], ret="int")
            assert result == 0 and not writes, (fn, client, key, result, writes)
