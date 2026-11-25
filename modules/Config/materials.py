"""
Material, fluid and propellant properties, loaded from `inputs/materials.toml`

Every value is stored in SI units. The input file may give a value in other
units together with a matching *_units key, and it is converted here on load
"""

#region Imports
from typing      import Any
from dataclasses import dataclass
from math        import pi, radians
from pathlib     import Path

import tomllib

from .constants  import CONSTANTS, INPUTS_DIR
from .validation import build, check_keys, require, require_positive
#endregion

#region Unit conversions to SI
DENSITY_TO_SI  = {"kg/m^3": 1.0, "g/cm^3": 1e3} # -> [kg/m^3]
STRESS_TO_SI   = {"Pa":     1.0, "MPa":    1e6} # -> [Pa]
ENTHALPY_TO_SI = {"j/mol":  1.0, "kj/mol": 1e3} # -> [J/mol]
BAR_TO_PA      = 1e5

def to_si(
	value : float,
	units : str,
	table : dict[str, float],
	key   : str,
) -> float:
	require(
		units in table,
		f"{key} must be one of {', '.join(table)} (got '{units}')",
	)
	return value * table[units]
#endregion

#region Gases
@dataclass(frozen=True)
class Air:
	"""Dry air as a calorically perfect ideal gas"""
	molar_mass : float  # Molar mass [kg/mol]
	gamma      : float  # Ratio of specific heats cp / cv [-]

	def __post_init__(self) -> None:
		require_positive(self, "molar_mass")
		require(
			self.gamma > 1.0,
			f"[air] gamma must be > 1 (got {self.gamma})"
		)

	@property
	def r_specific(self) -> float:
		"""Specific gas constant R / M [J/(kg*K)]"""
		return CONSTANTS.universal.molar_gas_constant / self.molar_mass

@dataclass(frozen=True)
class Gas:
	"""Pressurant gas"""
	name          : str    # Display name
	coolprop_name : str    # Fluid name in CoolProp, for real-gas model
	molar_mass    : float  # Molar mass [kg/mol]
	gamma         : float  # Ratio of specific heats cp/cv [-]
	z_factor      : float  # Full-bottle compressibility (ideal gas) [-]

	def __post_init__(self) -> None:
		require_positive(self, "molar_mass", "z_factor")
		require(
			self.gamma > 1.0,
			f"Gas '{self.name}' gamma must be > 1 (got {self.gamma})",
		)

	@property
	def r_specific(self) -> float:
		"""Specific gas constant R / M [J/(kg*K)]"""
		return CONSTANTS.universal.molar_gas_constant / self.molar_mass
#endregion

#region Structural materials and walls
@dataclass(frozen=True)
class Material:
	"""Structural material"""
	name              : str   # Display name
	density           : float # [kg/m^3]
	yield_strength    : float # Stress at onset of plastic flow [Pa]
	ultimate_strength : float # Stress at failure [Pa]

	def __post_init__(self) -> None:
		require_positive(
			self, "density", "yield_strength", "ultimate_strength",
		)
		require(
			self.ultimate_strength >= self.yield_strength,
			f"Material '{self.name}' ultimate_strength must be "
			f">= yield_strength",
		)

def _check_thickness(thickness: float | None, layer: str) -> None:
	require(
		thickness is None or thickness > 0,
		f"{layer} thickness must be > 0 (got {thickness})",
	)

@dataclass(frozen=True)
class MetalLayer:
	"""Isotropic metal layer, e.g. a tank liner"""
	# Layer material
	material  : Material
	# Fixed thickness [m]
	# When None: size to the tank pressure
	thickness : float | None

	def __post_init__(self) -> None:
		_check_thickness(
			self.thickness, f"Metal layer '{self.material.name}'",
		)

@dataclass(frozen=True)
class CompositeLayer:
	"""Filament-wound fiber composite layer"""
	# Layer material
	material          : Material
	# Fixed thickness [m]
	# When None: size to the tank pressure
	thickness         : float | None
	# Winding angle of the helical fibers to the tank axis [rad]
	helical_angle     : float
	# Share of the fiber strength the layer realizes [-]
	efficiency        : float
	# Fiber share of the layer volume [-]
	fiber_volume_frac : float

	def __post_init__(self):
		name = f"Composite layer '{self.material.name}'"
		_check_thickness(self.thickness, name)
		require(
			0.0 < self.helical_angle < 0.5 * pi,
			f"{name} helical angle must be in (0, 90) deg"
		)
		require(
			0.0 < self.efficiency <= 1.0,
			f"{name} efficiency must be in (0, 1]"
		)
		require(
			0.0 < self.fiber_volume_frac <= 1.0,
			f"{name} fiber_volume_frac must be in (0, 1]"
		)

Layer = MetalLayer | CompositeLayer

@dataclass(frozen=True)
class Wall:
	"""Tank wall layup"""
	layers : tuple[Layer, ...]  # Layers from the inside out

	def __post_init__(self) -> None:
		require(len(self.layers) > 0, "A wall needs at least one layer")
		require(
			sum(layer.thickness is None for layer in self.layers) <= 1,
			"At most one wall layer can be sized to the tank pressure",
		)
#endregion

#region Propellants
@dataclass(frozen=True)
class Species:
	"""One propellant reactant"""
	name           : str               # CEA or custom species name
	role           : str               # "fuel" or "oxid"
	mass_fraction  : float             # Relative share within role [-]
	formula        : dict[str, float]  # Atom counts, e.g. {"C": 25, "H": 52}
	temperature    : float             # Temperature at injection [K]
	enthalpy       : float | None      # Enthalpy of formation [J/mol]
	                                   # When None: use CEA library
	density        : float             # [kg/m^3]
	vapor_pressure : float | None      # Saturation pressure at storage
	                                   # temperature [Pa], oxidizer only

	def __post_init__(self):
		name = f"Species '{self.name}'"
		require(
			self.role in ("fuel", "oxid"),
			f"{name} role must be 'fuel' or 'oxid'",
		)
		require(
			len(self.formula) > 0,
			f"{name} needs a formula",
		)
		require_positive(
			self, "mass_fraction", "temperature", "density",
		)
		require(
			self.vapor_pressure is None or self.vapor_pressure > 0,
			f"{name} vapor pressure must be > 0",
		)

@dataclass(frozen=True)
class Propellants:
	"""Fuel blend and oxidizer of the hybrid engine"""
	fuels    : tuple[Species, ...]  # Fuel species, blended by mass_fraction
	oxidizer : Species              # Liquid oxidizer at saturation pressure

	def __post_init__(self):
		require(len(self.fuels) > 0, "At least one [[fuel]] is needed")
		for fuel in self.fuels:
			require(
				fuel.role == "fuel",
				f"Species '{fuel.name}' is not a fuel",
			)
			require(
				fuel.vapor_pressure is None,
				f"Fuel '{fuel.name}' cannot have a vapor_pressure_bar, "
				f"the grain is solid",
			)
		require(
			self.oxidizer.role == "oxid",
			f"Species '{self.oxidizer.name}' is not an oxidizer",
		)
		require(
			self.oxidizer.vapor_pressure is not None,
			f"Oxidizer '{self.oxidizer.name}' needs a vapor_pressure_bar "
			f"to size the pad gas",
		)
#endregion

#region Library
@dataclass(frozen=True)
class Materials:
	"""Everything in the materials file"""
	air         : Air             # Atmosphere gas
	walls       : dict[str, Wall] # Tank wall layups, by id
	gases       : dict[str, Gas]  # Pressurant gases, by id
	propellants : Propellants     # Fuel blend and oxidizer

	def wall(self, wall_id: str) -> Wall:
		avail = ", ".join(self.walls)
		require(
			wall_id in self.walls,
			f"Unknown wall '{wall_id}', materials file has: {avail}",
		)
		return self.walls[wall_id]

	def gas(self, gas_id: str) -> Gas:
		avail = ", ". join(self.gases)
		require(
			gas_id in self.gases,
			f"Unknown gas '{gas_id}', materials file has: {avail}",
		)
		return self.gases[gas_id]
#endregion

#region Loader
def _load_material(m: dict[str, Any]) -> tuple[str, Material]:
	section = f"material '{m.get('id')}'"
	check_keys(m, section, {
		"id", "name", "density", "density_units",
		"yield_strength", "ultimate_strength", "strength_units",
	})

	rho = to_si(
		m["density"], m["density_units"], DENSITY_TO_SI, "density_units",
	)
	ys = to_si(
		m["yield_strength"],
		m["strength_units"],
		STRESS_TO_SI,
		"strength_units",
	)
	uts = to_si(
		m["ultimate_strength"],
		m["strength_units"],
		STRESS_TO_SI,
		"strength_units",
	)

	return m["id"], Material(
		name              = m["name"],
		density           = rho,
		yield_strength    = ys,
		ultimate_strength = uts,
	)

def _load_layer(
	lay       : dict[str, Any],
	wall_id   : str,
	materials : dict[str, Material],
) -> Layer:
	section = f"wall '{wall_id}' layer"
	require(
		lay.get("material") in materials,
		f"[{section}]: unknown material '{lay.get('material')}', "
		f"the materials file has: {', '.join(materials)}",
	)
	material  = materials[lay["material"]]
	thickness = lay.get("thickness_m")

	# A layer with a winding angle is a composite, without one a metal
	if "helical_angle_deg" not in lay:
		check_keys(lay, section, {"material"}, {"thickness_m"})
		return MetalLayer(material=material, thickness=thickness)

	check_keys(
		lay, section,
		{
			"material",
			"helical_angle_deg",
			"efficiency",
			"fiber_volume_frac",
		},
		{ "thickness_m" },
	)
	return CompositeLayer(
		material          = material,
		thickness         = thickness,
		helical_angle     = radians(lay["helical_angle_deg"]),
		efficiency        = lay["efficiency"],
		fiber_volume_frac = lay["fiber_volume_frac"],
	)

def _load_species(s: dict, role: str) -> Species:
	section = f"{role} '{s.get('name')}'"
	check_keys(
		s, section,
		{
			"name",
			"mass_fraction",
			"formula_parts",
			"temperature_k",
			"density",
			"density_units",
		},
		{ "enthalpy", "enthalpy_units", "vapor_pressure_bar" },
	)
	require(
		("enthalpy" in s) == ("enthalpy_units" in s),
		f"[{section}]: enthalpy and enthalpy_units go together",
	)

	# Copolymers are given as parts, e.g. the three monomers of ABS
	formula: dict[str, float] = {}
	for part in s["formula_parts"]:
		for atom, count in part.items():
			formula[atom] = formula.get(atom, 0) + count

	enthalpy = None
	if "enthalpy" in s:
		enthalpy = to_si(
			s["enthalpy"],
			s["enthalpy_units"],
			ENTHALPY_TO_SI,
			"enthalpy_units",
		)

	vapor_pressure = None
	if "vapor_pressure_bar" in s:
		vapor_pressure = s["vapor_pressure_bar"] * BAR_TO_PA

	rho = to_si(
		s["density"], s["density_units"], DENSITY_TO_SI, "density_units",
	)

	return Species(
		name           = s["name"],
		role           = role,
		mass_fraction  = s["mass_fraction"],
		formula        = formula,
		temperature    = s["temperature_k"],
		enthalpy       = enthalpy,
		density        = rho,
		vapor_pressure = vapor_pressure,
	)

def load_materials(
	path: str | Path = INPUTS_DIR / "materials.toml"
) -> Materials:
	with open(path, "rb") as f:
		data = tomllib.load(f)

	check_keys(
		data,
		"materials file",
		{ "air", "material", "wall", "gas", "fuel", "oxid" },
	)

	materials = dict(_load_material(m) for m in data["material"])

	walls = {}
	for w in data["wall"]:
		check_keys(w, f"wall '{w.get('id')}'", {"id", "layers"})
		layers = tuple(
			_load_layer(lay, w["id"], materials) for lay in w["layers"]
		)
		walls[w["id"]] = Wall(layers)

	gases = {}
	for g in data["gas"]:
		g      = dict(g)
		gas_id = g.pop("id")
		gases[gas_id] = build(Gas, g, f"gas '{gas_id}'")

	require(
		len(data["oxid"]) == 1,
		"The materials file needs exactly one [[oxid]]"
	)

	return Materials(
		air         = build(Air, data["air"], "air"),
		walls       = walls,
		gases       = gases,
		propellants = Propellants(
			fuels    = tuple(_load_species(s, "fuel") for s in data["fuel"]),
			oxidizer = _load_species(data["oxid"][0], "oxid"),
		),
	)
#endregion
