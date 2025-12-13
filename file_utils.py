"""
File Utilities
--------------

Lightweight, dependency-free helpers for common file and filesystem tasks.
Provides a `FileUtils` class that can operate relative to an optional base
directory, plus convenience methods for reading/writing text and JSON, atomic
writes, directory operations, hashing, and simple path helpers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Iterator, Optional, Union
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile


PathLike = Union[str, os.PathLike[str]]


def _to_path(p: PathLike) -> Path:
    return p if isinstance(p, Path) else Path(p)


@dataclass
class FileUtils:
    base_dir: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.base_dir is not None and not isinstance(self.base_dir, Path):
            self.base_dir = Path(self.base_dir)

    # --------------- path helpers ---------------
    def resolve(self, path: PathLike) -> Path:
        p = _to_path(path)
        if not p.is_absolute() and self.base_dir is not None:
            p = self.base_dir / p
        return p

    @staticmethod
    def expanduser(path: PathLike) -> Path:
        return _to_path(path).expanduser()

    @staticmethod
    def ensure_suffix(path: PathLike, suffix: str) -> Path:
        p = _to_path(path)
        return p if str(p).endswith(suffix) else p.with_name(p.name + suffix)

    @staticmethod
    def change_ext(path: PathLike, new_ext: str) -> Path:
        if not new_ext.startswith('.'):
            new_ext = '.' + new_ext
        return _to_path(path).with_suffix(new_ext)

    # --------------- read/write ---------------
    def read_text(self, path: PathLike, *, encoding: str = "utf-8", errors: str = "strict") -> str:
        p = self.resolve(path)
        return p.read_text(encoding=encoding, errors=errors)

    def write_text(
        self,
        path: PathLike,
        data: str,
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
        newline: Optional[str] = None,
        make_dirs: bool = True,
    ) -> Path:
        p = self.resolve(path)
        if make_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding=encoding, errors=errors, newline=newline) as f:
            f.write(data)
        return p

    def append_text(
        self,
        path: PathLike,
        data: str,
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
        newline: Optional[str] = None,
        make_dirs: bool = True,
    ) -> Path:
        p = self.resolve(path)
        if make_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding=encoding, errors=errors, newline=newline) as f:
            f.write(data)
        return p

    def read_bytes(self, path: PathLike) -> bytes:
        return self.resolve(path).read_bytes()

    def write_bytes(self, path: PathLike, data: bytes, *, make_dirs: bool = True) -> Path:
        p = self.resolve(path)
        if make_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def read_lines(self, path: PathLike, *, encoding: str = "utf-8", errors: str = "strict") -> list[str]:
        text = self.read_text(path, encoding=encoding, errors=errors)
        # Preserve empty trailing line semantics by splitlines(True)? Keep simple:
        return text.splitlines()

    def write_lines(
        self,
        path: PathLike,
        lines: Iterable[str],
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
        newline: str = "\n",
        make_dirs: bool = True,
        ensure_trailing_newline: bool = True,
    ) -> Path:
        content = newline.join(lines)
        if ensure_trailing_newline and (not content.endswith(newline)):
            content += newline
        return self.write_text(path, content, encoding=encoding, errors=errors, newline=newline, make_dirs=make_dirs)

    # --------------- JSON helpers ---------------
    def read_json(self, path: PathLike, *, encoding: str = "utf-8") -> Any:
        with open(self.resolve(path), "r", encoding=encoding) as f:
            return json.load(f)

    def write_json(
        self,
        path: PathLike,
        obj: Any,
        *,
        encoding: str = "utf-8",
        indent: Optional[int] = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
        make_dirs: bool = True,
    ) -> Path:
        p = self.resolve(path)
        if make_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding=encoding) as f:
            json.dump(obj, f, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys)
        return p

    # --------------- atomic write ---------------
    def atomic_write_bytes(self, path: PathLike, data: bytes, *, make_dirs: bool = True) -> Path:
        p = self.resolve(path)
        if make_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        # Create temporary file in the same directory for atomic replace
        fd, tmp_path = tempfile.mkstemp(prefix=".tmp_", dir=str(p.parent))
        try:
            with os.fdopen(fd, "wb") as tmp:
                tmp.write(data)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, p)
        finally:
            with contextlib.suppress(FileNotFoundError):
                os.remove(tmp_path)
        return p

    def atomic_write_text(
        self,
        path: PathLike,
        data: str,
        *,
        encoding: str = "utf-8",
        errors: str = "strict",
        newline: Optional[str] = None,
        make_dirs: bool = True,
    ) -> Path:
        # Encode first to ensure consistent atomic path
        bio = io.BytesIO()
        w = io.TextIOWrapper(bio, encoding=encoding, errors=errors, newline=newline)
        try:
            w.write(data)
            w.flush()
            # Detach so closing the wrapper doesn't close the underlying buffer
            w.detach()
        finally:
            with contextlib.suppress(Exception):
                w.close()
        return self.atomic_write_bytes(path, bio.getvalue(), make_dirs=make_dirs)

    def atomic_write_json(
        self,
        path: PathLike,
        obj: Any,
        *,
        encoding: str = "utf-8",
        indent: Optional[int] = 2,
        ensure_ascii: bool = False,
        sort_keys: bool = False,
        make_dirs: bool = True,
    ) -> Path:
        data = json.dumps(obj, ensure_ascii=ensure_ascii, indent=indent, sort_keys=sort_keys)
        return self.atomic_write_text(path, data, encoding=encoding, make_dirs=make_dirs)

    # --------------- filesystem ops ---------------
    def exists(self, path: PathLike) -> bool:
        return self.resolve(path).exists()

    def is_file(self, path: PathLike) -> bool:
        return self.resolve(path).is_file()

    def is_dir(self, path: PathLike) -> bool:
        return self.resolve(path).is_dir()

    def size(self, path: PathLike) -> int:
        return self.resolve(path).stat().st_size

    def touch(self, path: PathLike, *, make_dirs: bool = True, exist_ok: bool = True) -> Path:
        p = self.resolve(path)
        if make_dirs:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.touch(exist_ok=exist_ok)
        return p

    def mkdirs(self, path: PathLike, *, exist_ok: bool = True) -> Path:
        p = self.resolve(path)
        p.mkdir(parents=True, exist_ok=exist_ok)
        return p

    def listdir(self, path: PathLike) -> list[Path]:
        p = self.resolve(path)
        return sorted([c for c in p.iterdir()], key=lambda x: x.name)

    def glob(self, path: PathLike, pattern: str) -> list[Path]:
        p = self.resolve(path)
        return sorted([c for c in p.glob(pattern)], key=lambda x: x.name)

    def remove(self, path: PathLike, *, missing_ok: bool = False) -> None:
        p = self.resolve(path)
        try:
            p.unlink()
        except FileNotFoundError:
            if not missing_ok:
                raise

    def rmtree(self, path: PathLike, *, missing_ok: bool = False) -> None:
        p = self.resolve(path)
        try:
            shutil.rmtree(p)
        except FileNotFoundError:
            if not missing_ok:
                raise

    def copy(self, src: PathLike, dst: PathLike, *, overwrite: bool = True, make_dirs: bool = True) -> Path:
        s = self.resolve(src)
        d = self.resolve(dst)
        if d.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {d}")
        if make_dirs:
            d_parent = d if d.suffix == '' and not d.exists() and str(d).endswith(os.sep) else d.parent
            d_parent.mkdir(parents=True, exist_ok=True)
        if d.is_dir() or (not d.exists() and str(d).endswith(os.sep)):
            # If destination indicates a directory, copy into it
            return Path(shutil.copy2(s, d / s.name))
        return Path(shutil.copy2(s, d))

    def move(self, src: PathLike, dst: PathLike, *, overwrite: bool = True, make_dirs: bool = True) -> Path:
        s = self.resolve(src)
        d = self.resolve(dst)
        if d.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {d}")
        if make_dirs:
            d.parent.mkdir(parents=True, exist_ok=True)
        return Path(shutil.move(str(s), str(d)))

    def rename(self, src: PathLike, dst: PathLike, *, overwrite: bool = True, make_dirs: bool = True) -> Path:
        s = self.resolve(src)
        d = self.resolve(dst)
        if d.exists() and not overwrite:
            raise FileExistsError(f"Destination exists: {d}")
        if make_dirs:
            d.parent.mkdir(parents=True, exist_ok=True)
        os.replace(s, d)
        return d

    # --------------- hashing ---------------
    def sha256_file(self, path: PathLike, *, chunk_size: int = 65536) -> str:
        p = self.resolve(path)
        h = hashlib.sha256()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                h.update(chunk)
        return h.hexdigest()

    def md5_file(self, path: PathLike, *, chunk_size: int = 65536) -> str:
        p = self.resolve(path)
        h = hashlib.md5()
        with open(p, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                h.update(chunk)
        return h.hexdigest()

    @contextlib.contextmanager
    def temporary_directory(self, *, prefix: str = "tmp_", dir: Optional[PathLike] = None) -> Iterator[Path]:
        base = self.resolve(dir) if dir is not None else None
        with tempfile.TemporaryDirectory(prefix=prefix, dir=str(base) if base is not None else None) as td:
            yield Path(td)
