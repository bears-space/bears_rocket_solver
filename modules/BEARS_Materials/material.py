#region Imports
from dataclasses import dataclass
#endregion

#region Material record
@dataclass(frozen=True)
class Material:
	name: str
	density:           float # [kg/m^3]
	yield_strength:    float # [Pa]
	ultimate_strength: float # [Pa]
	elastic_modulus:   float # [Pa]
#endregion

#region Standard aerospace presets
AL_6061_T6 = Material(
	name="Aluminum 6061-T6",
	density=2700.0,
	yield_strength=276e6,
	ultimate_strength=310e6,
	elastic_modulus=68.9e9
)

CFRP_T700 = Material(
	name="T700 Carbon Fiber / Epoxy",
	density=1550.0,
	yield_strength=1800e6,
	ultimate_strength=2100e6,
	elastic_modulus=135e9
)

SS_304 = Material(
	name="Stainless Steel 304",
	density=8000.0,
	yield_strength=215e6,
	ultimate_strength=505e6,
	elastic_modulus=193e9
)
#endregion

