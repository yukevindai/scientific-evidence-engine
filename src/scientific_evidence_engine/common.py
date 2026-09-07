"""Strict JSON, content identities, and immutable directory transactions."""
import hashlib
import json
import math
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from importlib.metadata import version
from pathlib import Path


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()


def identity(prefix, value):
    return prefix + "_" + sha256(canonical(value))


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def invalid(value):
        raise ValueError(f"Non-finite JSON value: {value}")
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")
    return value


def number(value, name, minimum=None):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name} must be a finite number")
    try:
        value = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(value) or (minimum is not None and value < minimum):
        raise ValueError(f"Invalid {name}: expected finite value >= {minimum}")
    return value


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


def fields(obj, required, optional=()):
    if not isinstance(obj, dict) or set(obj) - set(required) - set(optional) or set(required) - set(obj):
        raise ValueError(f"Expected required keys {sorted(required)} and optional keys {sorted(optional)}")


def safe_path(root, relative):
    text(relative, "relative path")
    root = Path(root).resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root):
        raise ValueError("Artifact path escapes its bundle")
    return path


def valid_id(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r"_[a-f0-9]{64}", value):
        raise ValueError(f"Invalid {prefix} identifier")
    return value


def versions():
    return {name: version(name) for name in ("scientific-evidence-engine", "numpy", "Pillow", "pypdfium2", "pint")}


@contextmanager
def new_directory(destination):
    """Never replace existing work; publish only after all files have been written."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}")
    temp = Path(tempfile.mkdtemp(prefix=".evidence-", dir=destination.parent))
    try:
        yield temp
        # Reserve the name exclusively before moving files; no overwrite races.
        destination.mkdir()
        try:
            for child in temp.iterdir():
                os.rename(child, destination / child.name)
        except BaseException:
            shutil.rmtree(destination)
            raise
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def finding(code, severity, message, action, rows=(), evidence=None):
    return dict(code=code, severity=severity, message=message, recommended_action=action,
                affected_rows=list(rows), evidence=evidence or {})
