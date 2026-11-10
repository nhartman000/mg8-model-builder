"""Deterministic offline checks for mg8.gitson-boundary-declaration.v1.

The frozen schema file is hashed as exact UTF-8 bytes. A mismatch refuses
to validate. The evaluator implements only the keywords that file uses.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

SCHEMA_ID = "mg8.gitson-boundary-declaration.v1"
SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schemas" / "gitson-boundary-declaration.v1.schema.json"
SCHEMA_DIGEST = "sha256:4761edfc48d1242ec36d768dde81633cc084877d5c94563ff6f26a28f3115a72"
MAX_BYTES_EXCLUSIVE = 500000

# Same tripwire as decision_console.core.FORBIDDEN_KEYS. It catches obvious
# key names. It is not a general prompt-content classifier.
FORBIDDEN_KEYS = frozenset({"prompt", "raw_prompt", "user_example", "example_prompt"})

_ALLOWED_SCHEMA_KEYS = frozenset({
    "$schema", "$id", "title", "description", "type", "const", "enum", "pattern",
    "minLength", "maxLength", "required", "additionalProperties", "properties",
    "items", "minItems", "maxItems", "uniqueItems",
})
_TYPES = frozenset({"object", "array", "string", "boolean", "integer", "number"})


class SchemaFreezeError(RuntimeError):
    pass


def canonical_json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _json_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right))
    if isinstance(left, dict):
        return len(left) == len(right) and all(k in right and _json_equal(left[k], right[k]) for k in left)
    return left == right


def _assert_supported(node: Any, path: str) -> None:
    if not isinstance(node, dict):
        raise SchemaFreezeError(f"{path} schema node must be an object")
    extra = set(node) - _ALLOWED_SCHEMA_KEYS
    if extra:
        raise SchemaFreezeError(f"{path} unsupported keywords {sorted(extra)}")
    if "type" in node and node["type"] not in _TYPES:
        raise SchemaFreezeError(f"{path} unsupported type")
    if "pattern" in node:
        pattern = node["pattern"]
        if not (isinstance(pattern, str) and pattern.startswith("^") and pattern.endswith("$")):
            raise SchemaFreezeError(f"{path} pattern must be anchored")
        re.compile(pattern)
    if node.get("type") == "object":
        if node.get("additionalProperties") is not False:
            raise SchemaFreezeError(f"{path} object must set additionalProperties false")
        props = node.get("properties", {})
        if not isinstance(props, dict):
            raise SchemaFreezeError(f"{path} properties must be an object")
        required = node.get("required", [])
        if not isinstance(required, list) or set(required) != set(props):
            raise SchemaFreezeError(f"{path} required must match properties")
        for key, sub in props.items():
            _assert_supported(sub, f"{path}.{key}")
    if "items" in node:
        _assert_supported(node["items"], path + ".items")


def _load_frozen_schema() -> dict:
    raw = SCHEMA_PATH.read_bytes()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != SCHEMA_DIGEST:
        raise SchemaFreezeError(f"frozen schema digest mismatch: file {digest} != {SCHEMA_DIGEST}")
    schema = json.loads(raw.decode("utf-8"))
    if schema.get("$id") != SCHEMA_ID:
        raise SchemaFreezeError("schema $id mismatch")
    _assert_supported(schema, "$")
    return schema


SCHEMA = _load_frozen_schema()


def _type_ok(expected: str, instance: Any) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, (int, float)) and not isinstance(instance, bool) and instance == instance
    return False


def _reject_duplicate_keys(pairs: list) -> dict:
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate key {key!r}")
        obj[key] = value
    return obj


def _walk_forbidden(obj: Any, path: str, reasons: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in FORBIDDEN_KEYS:
                reasons.append(f"forbidden key {key} at {path}")
            _walk_forbidden(value, f"{path}.{key}", reasons)
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            _walk_forbidden(value, f"{path}[{index}]", reasons)


def _validate_node(schema: dict, instance: Any, path: str, reasons: list[str]) -> None:
    if "const" in schema and not _json_equal(instance, schema["const"]):
        reasons.append(f"schema: {path} expected const {schema['const']!r}")
        return
    if "enum" in schema and not any(_json_equal(instance, item) for item in schema["enum"]):
        reasons.append(f"schema: {path} value not in enum")
        return
    expected = schema.get("type")
    if expected is not None and not _type_ok(expected, instance):
        reasons.append(f"schema: {path} expected type {expected}")
        return
    if expected == "object":
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                reasons.append(f"schema: {path} missing required property {key}")
        for key in sorted(instance):
            if key in props:
                continue
            if key in FORBIDDEN_KEYS:
                continue
            shown = key if len(key) <= 80 else key[:80] + "..."
            reasons.append(f"schema: {path} unknown property {shown}")
        for key, sub in props.items():
            if key in instance:
                _validate_node(sub, instance[key], f"{path}.{key}", reasons)
    elif expected == "array":
        minimum = schema.get("minItems")
        maximum = schema.get("maxItems")
        if minimum is not None and len(instance) < minimum:
            reasons.append(f"schema: {path} has {len(instance)} items; minimum is {minimum}")
        if maximum is not None and len(instance) > maximum:
            reasons.append(f"schema: {path} has {len(instance)} items; maximum is {maximum}")
        if schema.get("uniqueItems"):
            seen: list[Any] = []
            for item in instance:
                if any(_json_equal(item, prior) for prior in seen):
                    reasons.append(f"schema: {path} duplicate items")
                    break
                seen.append(item)
        item_schema = schema["items"]
        for index, item in enumerate(instance):
            _validate_node(item_schema, item, f"{path}[{index}]", reasons)
    elif expected == "string":
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, instance) is None:
            reasons.append(f"schema: {path} does not match pattern")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            reasons.append(f"schema: {path} shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            reasons.append(f"schema: {path} longer than maxLength {schema['maxLength']}")


def _semantic(data: dict, reasons: list[str]) -> None:
    source = data["source"]["module_id"]
    target = data["target"]["module_id"]
    if source == target:
        reasons.append("semantic: source.module_id equals target.module_id")
    seen: list[str] = []
    for item in data["upstream_evidence"]:
        module_id = item["module_id"]
        expected = "I" + module_id[1:]
        if item["inspector_id"] != expected:
            reasons.append(
                f"semantic: inspector {item['inspector_id']} is not the paired inspector {expected} for {module_id}"
            )
        if module_id in seen:
            reasons.append(f"semantic: duplicate upstream evidence for {module_id}")
        else:
            seen.append(module_id)
    if source != "INTEGRATION" and source not in seen:
        reasons.append(f"semantic: upstream PASS evidence does not include source module {source}")


def _result(reasons: list[str], size: int) -> dict:
    unique = sorted(set(reasons))
    return {
        "verdict": "PASS" if not unique else "FAIL",
        "reasons": unique,
        "schema": SCHEMA_ID,
        "schema_digest": SCHEMA_DIGEST,
        "size_bytes": size,
        "max_bytes_exclusive": MAX_BYTES_EXCLUSIVE,
    }


def validate_declaration(document: bytes | str) -> dict:
    """Return a PASS/FAIL result. The result never echoes declaration values."""
    if isinstance(document, str):
        raw = document.encode("utf-8")
    elif isinstance(document, (bytes, bytearray)):
        raw = bytes(document)
    else:
        raise TypeError("declaration must be bytes or str")
    reasons: list[str] = []
    size = len(raw)
    if size >= MAX_BYTES_EXCLUSIVE:
        reasons.append(
            f"size: serialized UTF-8 is {size} bytes; limit is exclusive {MAX_BYTES_EXCLUSIVE}"
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        reasons.append("utf-8: declaration is not valid UTF-8")
        return _result(reasons, size)
    try:
        data = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as err:
        reasons.append(f"json: {err.msg}")
        return _result(reasons, size)
    except ValueError as err:
        reasons.append(f"json: {err}")
        return _result(reasons, size)
    _walk_forbidden(data, "$", reasons)
    schema_at = len(reasons)
    _validate_node(SCHEMA, data, "$", reasons)
    schema_failed = any(reason.startswith("schema:") for reason in reasons[schema_at:])
    if not schema_failed and isinstance(data, dict):
        _semantic(data, reasons)
    return _result(reasons, size)
