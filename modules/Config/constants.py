"""
Physical constants, loaded once on import from `inputs/constants.toml`

Every physical constant the solver uses is read from the `CONSTANTS` instance
below. Material properties and design inputs have their own input files, see
`materials.py` and `rocket.py`
"""

#region Imports
from dataclasses import dataclass
from pathlib     import Path

import tomllib

from .validation import build, require, require_positive
#endregion

INPUTS_DIR = Path(__file__).resolve().parents[2] / "inputs"

#region Records
@dataclass(frozen=True)
class UniversalConstants:
	standard_gravity   : float  # Standard gravity g0 [m/s^2]
	molar_gas_constant : float  # Molar gas constant R [J/(mol*K)]
	zero_celsius       : float  # 0 degC on the absolute scale [K]

	def __post_init__(self) -> None:
		require_positive(
			self,
			"standard_gravity",
			"molar_gas_constant",
			"zero_celsius",
		)

@dataclass(frozen=True)
class StandardAtmosphere:
	sea_level_pressure     : float  # ISA pressure at sea level [Pa]
	sea_level_temperature  : float  # ISA temperature at sea level [K]
	lapse_rate             : float  # ISA temperature lapse rate [K/m]
	tropopause_temperature : float  # ISA temperature at tropopause [K]

	def __post_init__(self) -> None:
		require_positive(
			self,
			"sea_level_pressure",
			"sea_level_temperature",
			"lapse_rate",
			"tropopause_temperature",
		)
		require(
			self.tropopause_temperature < self.sea_level_temperature,
			"[atmosphere] tropopause_temperature must be below "
			"sea_level_temperature",
		)

@dataclass(frozen=True)
class PhysicalConstants:
	universal  : UniversalConstants  # Universal constants
	atmosphere : StandardAtmosphere  # International Standard Atmosphere
#endregion

def load_constants(
	path: str | Path = INPUTS_DIR / "constants.toml"
) -> PhysicalConstants:
	with open(path, "rb") as f:
		data = tomllib.load(f)

	return PhysicalConstants(
		universal  = build(UniversalConstants, data["universal"],  "universal"),
		atmosphere = build(
			StandardAtmosphere, data["atmosphere"], "atmosphere",
		),
	)

CONSTANTS = load_constants()
