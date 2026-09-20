#!/usr/bin/python3
"""Run an absolute executable with a closed env, deadline, and output caps."""

from __future__ import annotations

import os
import select
import signal
import subprocess
import sys
import time

EXIT_TIMEOUT = 124
EXIT_OVERFLOW = 125
EXIT_MISSING = 127

_ALLOWED = (
    "HOME",
    "USER",
    "LOGNAME",
    "XDG_CONFIG_HOME",
    "XDG_STATE_HOME",
    "XDG_RUNTIME_DIR",
    "XDG_DATA_HOME",
    "HYPRLAND_INSTANCE_SIGNATURE",
    "WAYLAND_DISPLAY",
    "DBUS_SESSION_BUS_ADDRESS",
    "XDG_SESSION_TYPE",
)


def closed_env() -> dict[str, str]:
    env = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    for key in _ALLOWED:
        val = os.environ.get(key)
        if val:
            env[key] = val
    return env


def _ingest(fd, buf: bytearray, cap: int) -> tuple[bool, bool]:
    try:
        chunk = os.read(fd.fileno(), 4096)
    except OSError:
        return True, False
    if not chunk:
        return True, False
    room = cap - len(buf)
    if room <= 0:
        return False, True
    if len(chunk) > room:
        buf.extend(chunk[:room])
        return False, True
    buf.extend(chunk)
    return False, False


def _kill_group(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        try:
            proc.kill()
        except OSError:
            pass


def _trusted_exe(path: str) -> bool:
    if not path or "\x00" in path:
        return False
    if not os.path.isabs(path):
        return False
    if ".." in path.split("/"):
        return False
    return path.startswith("/usr/bin/") or path.startswith("/bin/")


def run(
    argv: list[str],
    *,
    timeout: float,
    max_stdout: int,
    max_stderr: int,
) -> tuple[int, bytes, bytes]:
    if not argv or not _trusted_exe(argv[0]):
        raise SystemExit("refusing untrusted executable")
    if not os.path.isfile(argv[0]) or not os.access(argv[0], os.X_OK):
        return EXIT_MISSING, b"", b""
    try:
        proc = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd="/",
            env=closed_env(),
            start_new_session=True,
        )
    except OSError:
        return EXIT_MISSING, b"", b""
    stdout = bytearray()
    stderr = bytearray()
    stdout_eof = False
    stderr_eof = False
    truncated = False
    timed_out = False
    deadline = time.monotonic() + timeout
    try:
        while not (stdout_eof and stderr_eof):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            pipes = []
            if not stdout_eof and proc.stdout is not None:
                pipes.append(proc.stdout)
            if not stderr_eof and proc.stderr is not None:
                pipes.append(proc.stderr)
            if not pipes:
                break
            ready, _, _ = select.select(pipes, [], [], min(remaining, 0.05))
            if not ready and proc.poll() is not None:
                ready, _, _ = select.select(pipes, [], [], 0)
                if not ready:
                    break
            for fd in ready:
                if fd is proc.stdout:
                    eof, overflow = _ingest(fd, stdout, max_stdout)
                    stdout_eof = stdout_eof or eof
                    truncated = truncated or overflow
                else:
                    eof, overflow = _ingest(fd, stderr, max_stderr)
                    stderr_eof = stderr_eof or eof
                    truncated = truncated or overflow
            if truncated:
                break
    finally:
        if truncated or timed_out or proc.poll() is None:
            _kill_group(proc)
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            proc.wait(timeout=1)
        for fd in (proc.stdout, proc.stderr):
            if fd is not None:
                fd.close()
    if timed_out:
        return EXIT_TIMEOUT, b"", b""
    if truncated:
        return EXIT_OVERFLOW, b"", b""
    code = proc.returncode if proc.returncode is not None else EXIT_TIMEOUT
    return code, bytes(stdout), bytes(stderr)


def main(argv: list[str]) -> None:
    timeout = 8.0
    max_stdout = 65536
    max_stderr = 65536
    args = argv[1:]
    while args:
        if args[0] == "--timeout" and len(args) >= 2:
            timeout = float(args[1])
            args = args[2:]
        elif args[0] == "--max-stdout" and len(args) >= 2:
            max_stdout = int(args[1])
            args = args[2:]
        elif args[0] == "--max-stderr" and len(args) >= 2:
            max_stderr = int(args[1])
            args = args[2:]
        elif args[0] == "--":
            args = args[1:]
            break
        else:
            break
    if not args:
        raise SystemExit("usage: run.py [--timeout SEC] [--max-stdout N] [--max-stderr N] -- CMD ...")
    code, stdout, stderr = run(args, timeout=timeout, max_stdout=max_stdout, max_stderr=max_stderr)
    if stdout:
        sys.stdout.buffer.write(stdout)
        sys.stdout.buffer.flush()
    if stderr:
        sys.stderr.buffer.write(stderr)
        sys.stderr.buffer.flush()
    raise SystemExit(code)


if __name__ == "__main__":
    main(sys.argv)
