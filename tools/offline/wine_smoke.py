#!/usr/bin/env python3
"""Bounded Linux/Wine startup diagnostic for a verified custom package.

Blocks non-Unix socket creation in the launched process tree. This deliberately
prevents even custom UDP: use it to diagnose startup, not to test multiplayer.
It is not a Windows sandbox or a guarantee against host IPC brokers.
"""
import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time


def deny_ip_sockets():
    if sys.platform != 'linux' or platform.machine() != 'x86_64':
        raise RuntimeError('This diagnostic requires x86-64 Linux and libseccomp')
    lib = ctypes.CDLL(ctypes.util.find_library('seccomp') or 'libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]

    class Compare(ctypes.Structure):
        _fields_ = [('arg', ctypes.c_uint), ('op', ctypes.c_uint),
                    ('a', ctypes.c_uint64), ('b', ctypes.c_uint64)]

    context = lib.seccomp_init(0x7FFF0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError('seccomp_init failed')
    try:
        # SCMP_CMP_NE: permit AF_UNIX only. Block io_uring's alternate socket API.
        rules = [('socket', (Compare(0, 1, 1, 0),)), ('io_uring_setup', ())]
        for name, comparisons in rules:
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            if nr < 0 or lib.seccomp_rule_add(context, 0x50001, nr, len(comparisons), *comparisons):
                raise RuntimeError('Cannot install socket policy: ' + name)
        if lib.seccomp_load(context):
            raise RuntimeError('seccomp_load failed')
    finally:
        lib.seccomp_release(context)


def self_test():
    import socket
    try:
        socket.socket(socket.AF_UNIX).close()
        unix_available = True
    except PermissionError:
        unix_available = False
    program = '''import socket, subprocess, sys
for family in (socket.AF_INET, socket.AF_INET6, socket.AF_NETLINK):
    try: socket.socket(family)
    except PermissionError: pass
    else: raise AssertionError(family)
if sys.argv[1] == 'True': socket.socket(socket.AF_UNIX).close()
subprocess.run([sys.executable, '-c', "import socket; socket.socket(socket.AF_INET)"],
               check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 1 or sys.exit(2)
print('PASS: IP/netlink sockets denied; exec child inherits policy; host Unix sockets available:', sys.argv[1])
'''
    subprocess.run([sys.executable, '-c', program, str(unix_available)], preexec_fn=deny_ip_sockets, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', action='store_true')
    parser.add_argument('--wine', type=Path)
    parser.add_argument('--wineserver', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--game', type=Path)
    parser.add_argument('--prefix', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if not all((args.wine, args.wineserver, args.package, args.game, args.prefix, args.output)):
        parser.error('wine, wineserver, package, game, prefix and output are required')
    if not 1 <= args.seconds <= 300:
        parser.error('seconds must be 1..300')
    package, game, prefix = (p.resolve() for p in (args.package, args.game, args.prefix))
    manifest = json.loads((package / 'manifest.json').read_text())
    for name, key in [('iw6mp64_offline.exe', 'exe_sha256'), ('recon.dll', 'dll_sha256')]:
        if hashlib.sha256((package / name).read_bytes()).hexdigest() != manifest[key]:
            raise ValueError('Package hash mismatch: ' + name)
    if manifest['mode'] not in ('direct', 'offline'):
        raise ValueError('Not a custom package')
    args.output.mkdir(parents=True, exist_ok=False)
    prefix.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, WINEPREFIX=str(prefix), WINEARCH='win64',
               WINESERVER=str(args.wineserver.resolve()),
               WINEDLLOVERRIDES='mscoree,mshtml=', WINEDEBUG='+timestamp,+pid,+loaddll,+seh')
    # No proxy descriptors or proxy configuration are handed to Wine.
    env = {k: v for k, v in env.items() if 'proxy' not in k.lower()}
    arguments = args.arguments[1:] if args.arguments[:1] == ['--'] else args.arguments
    command = [str(args.wine.resolve()), str(package / 'iw6mp64_offline.exe'), *arguments]
    start = time.monotonic()
    timed_out = False
    with (args.output / 'stdout.log').open('wb') as out, (args.output / 'wine.log').open('wb') as err:
        process = subprocess.Popen(command, cwd=game, env=env, stdout=out, stderr=err,
                                   close_fds=True, start_new_session=True, preexec_fn=deny_ip_sockets)
        try:
            code = process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            code = process.wait()
        finally:
            subprocess.run([str(args.wineserver.resolve()), '-k'], env=env,
                           stdout=out, stderr=err, timeout=10, preexec_fn=deny_ip_sockets)
    report = {'mode': manifest['mode'], 'exe_sha256': manifest['exe_sha256'],
              'dll_sha256': manifest['dll_sha256'], 'exit_code': code, 'timed_out': timed_out,
              'elapsed_seconds': round(time.monotonic() - start, 2),
              'socket_policy': 'AF_UNIX only; io_uring_setup denied',
              'native_windows_verified': False, 'game_join_verified': False}
    (args.output / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
