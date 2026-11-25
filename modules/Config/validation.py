"""
Shared helpers for the input records

Every record checks itself in `__post_init__`, so any record that exists holds
valid values. These helpers keep those checks short
"""

#region Imports
from dataclasses import fields
from typing      import Any, TypeVar, cast
#endregion

T = TypeVar("T")

class ConfigValidationError(ValueError):
	"""An input value or input file key breaks a physical or logical rule"""

def require(condition: bool, message: str) -> None:
	if not condition: raise ConfigValidationError(message)

def require_positive(record: object, *names: str) -> None:
	"""Require each named field of `record` to be > 0"""
	for name in names:
		value = getattr(record, name)
		require(
			value > 0,
			f"{type(record).__name__}.{name} must be > 0 (got {value})"
		)

def check_keys(
	table    : dict[str, Any],
	section  : str,
	required : set[str],
	optional : set[str] | frozenset[str] = frozenset(),
) -> None:
	"""Reject unknown and missing keys so typos are reported, not ignored"""
	unknown = sorted(set(table) - required - optional)
	missing = sorted(required - set(table))

	problems = []
	if unknown: problems.append(f"unknown key(s) {', '.join(unknown)}")
	if missing: problems.append(f"missing key(s) {', '.join(missing)}")
	require(not problems, f"[{section}]: {'; '.join(problems)}")

def build(
	cls,
	table     : dict[str, Any],
	section   : str,
	**derived : Any,
):
	"""Construct `cls` from a TOML table whose keys match its fields"""
	req = {f.name for f in fields(cast(Any, cls))} - set(derived)
	check_keys(table, section, req)
	return cls(**table, **derived)
