#!/usr/bin/python3
"""Descriptor-relative, no-follow reads/writes.

Every destination component is opened from a retained directory descriptor
with O_NOFOLLOW. Missing parents are created with mkdirat on that descriptor,
never Path.mkdir on the full pathname.
"""

from __future__ import annotations

import errno
import os
import stat
import sys
from pathlib import Path

MAX_BYTES = 1_048_576


def die(msg: str) -> None:
    raise SystemExit(msg)


def _owned_by(st: os.stat_result, uid: int) -> bool:
    return st.st_uid == uid


def _allowed_dir_uids() -> set[int]:
    allowed = {0, os.getuid()}
    sudo_uid = os.environ.get("SUDO_UID")
    if sudo_uid and sudo_uid.isdigit() and int(sudo_uid) > 0:
        allowed.add(int(sudo_uid))
    return allowed


def _check_dir(st: os.stat_result, label: str) -> None:
    if not stat.S_ISDIR(st.st_mode):
        die(f"not a directory: {label}")
    if st.st_uid not in _allowed_dir_uids():
        die(f"unowned directory: {label}")
    if st.st_mode & 0o022:
        die(f"group- or world-writable directory: {label}")


def _abs_parts(path: Path) -> tuple[list[str], str]:
    raw = str(path)
    if not os.path.isabs(raw):
        die(f"path must be absolute: {path}")
    parts: list[str] = []
    for part in raw.split("/"):
        if part == "" or part == ".":
            continue
        if part == ".." or "\x00" in part:
            die(f"illegal path component: {path}")
        parts.append(part)
    if not parts:
        die(f"refusing root path: {path}")
    return parts[:-1], parts[-1]


def _open_walk(parts: list[str], *, create: bool) -> int:
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        _check_dir(os.fstat(fd), "/")
        walked = ""
        for part in parts:
            walked += "/" + part
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
            try:
                nxt = os.open(part, flags, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                try:
                    os.mkdir(part, 0o700, dir_fd=fd)
                except FileExistsError:
                    pass
                nxt = os.open(part, flags, dir_fd=fd)
            except OSError as exc:
                if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                    try:
                        st = os.stat(part, dir_fd=fd, follow_symlinks=False)
                    except OSError:
                        raise exc from None
                    if stat.S_ISLNK(st.st_mode):
                        die(f"refusing symlink: {walked}")
                raise
            os.close(fd)
            fd = nxt
            _check_dir(os.fstat(fd), walked)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _parent_dirfd(path: Path, *, create: bool) -> int:
    parent_parts, _name = _abs_parts(path)
    try:
        return _open_walk(parent_parts, create=create)
    except FileNotFoundError:
        die(f"missing parent of {path}")
    except OSError as exc:
        die(f"refusing parent of {path}: {exc}")


def read_text(path: Path, *, missing: str | None = None, owner: int | None = None) -> str:
    want = os.getuid() if owner is None else owner
    parent_parts, name = _abs_parts(path)
    try:
        dirfd = _open_walk(parent_parts, create=False)
    except FileNotFoundError:
        if missing is not None:
            return missing
        die(f"missing {path}")
    except OSError as exc:
        die(f"refusing parent of {path}: {exc}")
    try:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dirfd)
        except FileNotFoundError:
            if missing is not None:
                return missing
            die(f"missing {path}")
        except OSError as exc:
            die(f"refusing to read {path}: {exc}")
        try:
            st = os.fstat(fd)
            if not stat.S_ISREG(st.st_mode):
                die(f"refusing non-regular file: {path}")
            if not _owned_by(st, want):
                die(f"file not owned by uid {want}: {path}")
            if st.st_size > MAX_BYTES:
                die(f"file too large ({st.st_size} bytes): {path}")
            data = os.read(fd, MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                die(f"file too large: {path}")
            return data.decode()
        finally:
            os.close(fd)
    finally:
        os.close(dirfd)


def atomic_write(
    path: Path,
    text: str,
    *,
    create_parent: bool = True,
    mode: int = 0o600,
    owner: int | None = None,
) -> None:
    want = os.getuid() if owner is None else owner
    data = text.encode()
    if len(data) > MAX_BYTES:
        die(f"refusing to write oversized file: {path}")
    _parent_parts, name = _abs_parts(path)
    dirfd = _parent_dirfd(path, create=create_parent)
    tmp = f".{name}.{os.getpid()}.tmp"
    fd = -1
    try:
        try:
            existing = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing is not None:
            if stat.S_ISLNK(existing.st_mode) or not stat.S_ISREG(existing.st_mode):
                die(f"refusing non-regular file: {path}")
            if not _owned_by(existing, want):
                die(f"file not owned by uid {want}: {path}")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
        fd = os.open(tmp, flags, 0o600, dir_fd=dirfd)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not _owned_by(st, os.getuid()):
            die(f"refusing temp file {tmp}")
        written = 0
        while written < len(data):
            written += os.write(fd, data[written:])
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.rename(tmp, name, src_dir_fd=dirfd, dst_dir_fd=dirfd)
        landed = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        if stat.S_ISLNK(landed.st_mode) or not stat.S_ISREG(landed.st_mode):
            die(f"rename did not land on a regular file: {path}")
        if not _owned_by(landed, os.getuid()):
            die(f"renamed file not owned by current user: {path}")
        if mode != 0o600:
            os.chmod(name, mode, dir_fd=dirfd, follow_symlinks=False)
    except BaseException:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(tmp, dir_fd=dirfd)
        except FileNotFoundError:
            pass
        except OSError:
            pass
        raise
    finally:
        os.close(dirfd)


def copy_file(src: Path, dst: Path) -> None:
    atomic_write(dst, read_text(src))


def remove_file(path: Path) -> None:
    parent_parts, name = _abs_parts(path)
    try:
        dirfd = _open_walk(parent_parts, create=False)
    except FileNotFoundError:
        return
    except OSError:
        return
    try:
        try:
            st = os.stat(name, dir_fd=dirfd, follow_symlinks=False)
        except FileNotFoundError:
            return
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
            die(f"refusing non-regular file: {path}")
        if not _owned_by(st, os.getuid()):
            die(f"file not owned by current user: {path}")
        os.unlink(name, dir_fd=dirfd)
    finally:
        os.close(dirfd)


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        die("usage: safe_file.py copy SRC DST | remove PATH")
    action = argv[1]
    if action == "copy" and len(argv) == 4:
        copy_file(Path(argv[2]), Path(argv[3]))
    elif action == "remove" and len(argv) == 3:
        remove_file(Path(argv[2]))
    else:
        die("usage: safe_file.py copy SRC DST | remove PATH")


if __name__ == "__main__":
    main(sys.argv)
