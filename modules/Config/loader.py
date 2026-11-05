#region Imports
from dataclasses import dataclass
from pathlib     import Path

import tomllib

from .records import (
	MaterialConfig,
	GasConfig,
	WallConfig,
	MaterialsConfig,
	FluidsConfig,
	GlobalConfig,
	TankConfig,
	InjectorConfig,
	FuelConfig,
	IgniterConfig,
	NozzleConfig,
	OptimizationSeedConfig,
	EfficienciesConfig,
	SpeciesConfig,
	BipropellantConfig,
	PropellantConfig,
	RocketConfig,
)

from .validation import validate_rocket_config, validate_bipropellant_config
#endregion

def deep_merge(base: dict, overlay: dict) -> dict:
	# Helper function for merging dictionaries
	merged = dict(base)
	for k, v in overlay.items():
		if (
			k in merged
			and isinstance(merged[k], dict)
			and isinstance(v, dict)
		):
			merged[k] = deep_merge(merged[k], v)
		else:
			merged[k] = v

	return merged

def load_configs(
	path         : str | Path | None = "inputs/rocket.toml",
	default_path : str | Path        = "inputs/rocket.default.toml",
	validate     : bool              = True,
) -> RocketConfig:
	with open(default_path, "rb") as f:
		data = tomllib.load(f)

	if path is not None:
		user_file = Path(path)

		if (
			user_file.exists()
			and user_file.resolve() != Path(default_path).resolve()
		):
			with open(user_file, "rb") as f:
				n_data = tomllib.load(f)
				data = deep_merge(data, n_data)

	ox = data["oxidizer_tank"]
	pr = data["pressurizer_tank"]

	c_gl = GlobalConfig(**data["global"])

	c_ox = TankConfig(
		pressure_bar      = ox["pressure_bar"],
		diam_m            = ox["diam_m"],
		safety_factor     = ox["safety_factor"],
		yield_factor_pa   = ox["yield_factor_pa"],
		wall_density_kgm3 = ox["wall_density_kgm3"],
		ullage_fraction   = ox.get("ullage_fraction",   0.0),
		boss_opening_m    = ox.get("boss_opening_m",    0.02),
		boss_length_fwd_m = ox.get("boss_length_fwd_m", 0.015),
		boss_length_aft_m = ox.get("boss_length_aft_m", 0.019),
	)

	c_pr = TankConfig(
		pressure_bar      = pr["pressure_bar"],
		diam_m            = pr["diam_m"],
		safety_factor     = pr["safety_factor"],
		yield_factor_pa   = pr["yield_factor_pa"],
		wall_density_kgm3 = pr["wall_density_kgm3"],
		ullage_fraction   = pr.get("ullage_fraction",   0.0),
		boss_opening_m    = ox.get("boss_opening_m",    0.02),
		boss_length_fwd_m = ox.get("boss_length_fwd_m", 0.015),
		boss_length_aft_m = ox.get("boss_length_aft_m", 0.019),
		reg_margin_bar    = ox.get("reg_margin_bar",    20.0),
		ambient_temp_c    = ox.get("ambient_temp_c",    30.0),
	)

	c_in = InjectorConfig(**data["injector"])

	c_fu = FuelConfig(**data["fuel"])

	ign = data.get("igniter", {})
	c_ig = IgniterConfig(
		burn_time_s           = ign.get("burn_time_s",           1.0),
		burn_rate_ms          = ign.get("burn_rate_ms",          0.0015),
		flame_spread_ms       = ign.get("flame_spread_ms",       0.15),
		max_spread_delay_s    = ign.get("max_spread_delay_s",    0.10),
		thermite_density_kgm3 = ign.get("thermite_density_kgm3", 3800.0),
	)

	c_nz = NozzleConfig(**data["nozzle"])

	c_op = OptimizationSeedConfig(**data["optimization"])

	eff = data.get("efficiencies", {})
	c_ef = EfficienciesConfig(
		combustion             = eff.get("combustion",             0.88),
		trajectory             = eff.get("trajectory",             0.92),
		propellant_utilization = eff.get("propellant_utilization", 0.92),
		regression_correction  = eff.get("regression_correction",  0.60),
		nozzle_friction        = eff.get("nozzle_friction",        0.60),
	)

	cfg = RocketConfig(
		cfg_global       = c_gl,
		cfg_oxy_tank     = c_ox,
		cfg_press_tank   = c_pr,
		cfg_injector     = c_in,
		cfg_fuel         = c_fu,
		cfg_igniter      = c_ig,
		cfg_nozzle       = c_nz,
		cfg_optim        = c_op,
		cfg_efficiencies = c_ef,
	)

	if validate: validate_rocket_config(cfg)

	return cfg

def load_reactants(
	path     : str | Path,
	validate : bool = True,
) -> BipropellantConfig:
	with open(path, "rb") as f:
		data = tomllib.load(f)

	def parse_entry(r: dict, role: str) -> SpeciesConfig:
		return SpeciesConfig(
			name           = r["name"],
			formula_parts  = tuple(r.get("formula_parts", ())),
			mass_fraction  = r.get("mass_fraction", 100.0),
			temperature_k  = r.get("temperature_k", 298.15),
			enthalpy       = r.get("enthalpy"),
			enthalpy_units = r.get("enthalpy_units"),
			density        = r.get("density"),
			density_units  = r.get("density_units"),
			role           = role,
		)

	fuels = tuple(parse_entry(r, "fuel") for r in data["fuel"])
	oxids = tuple(parse_entry(r, "oxid") for r in data["oxid"])

	cfg = BipropellantConfig(fuels=fuels, oxidizers=oxids)

	if validate: validate_bipropellant_config(cfg)

	return cfg

def load_materials(path: str | Path) -> MaterialsConfig:
	with open(path, "rb") as f:
		data = tomllib.load(f)

	materials = []
	for m in data.get("material", []):
		rho = m["density"]
		if m.get("density_units") in ("g/cm^3", "g/cc", "g/cm3"):
			rho *= 1000.0

		ys = m["yield_strength"]
		us = m["ultimate_strength"]
		if m.get("strength_units") == "MPa":
			ys *= 1e6
			us *= 1e6

		em = m["elastic_modulus"]
		if m.get("modulus_units") == "GPa":
			em *= 1e9

		materials.append(MaterialConfig(
			id                = m["id"],
			name              = m["name"],
			density           = rho,
			yield_strength    = ys,
			ultimate_strength = us,
			elastic_modulus   = em,
		))

	walls = []
	for w in data.get("wall", []):
		layers = []
		for lay in w["layers"]:
			layers.append(LayerConfig(
				material_id       = lay["material"],
				thickness_m       = lay.get("thickness_m"),
				is_load_bearing   = lay.get("is_load_bearing", True),
				helical_angle_deg = lay.get("helical_angle_deg"),
				efficiency        = lay.get("efficiency", 0.85),
				fiber_volume_frac = lay.get("fiber_volume_frac", 0.72),
			))

		walls.append(WallConfig(id=w["id"], layers=tuple(layers)))

	return MaterialsConfig(materials=tuple(materials), walls=tuple(walls))

def load_fluids(path: str | Path) -> FluidsConfig:
	with open(path, "rb") as f:
		data = tomllib.load(f)

	gases = []
	for g in data.get("gas", []):
		gases.append(GasConfig(
			id         = g["id"],
			name       = g["name"],
			molar_mass = g["molar_mass"],
			gamma      = g["gamma"],
			z_factor   = g.get("z_factor", 1.0),
		))

	return FluidsConfig(gases=tuple(gases))
