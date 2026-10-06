#region Imports
from dataclasses import dataclass
from pathlib     import Path

import tomllib

from .records import (
	GlobalConfig,
	TankConfig,
	InjectorConfig,
	FuelConfig,
	NozzleConfig,
	OptimizationSeedConfig,
	ReactantConfig,
	MixtureConfig,
	RocketConfig,
)
#endregion

def deep_merge(base: dict, overlay: dict) -> dict:
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
		ullage_fraction   = ox.get("ullage_fraction", 0.0),
	)

	c_pr = TankConfig(
		pressure_bar      = pr["pressure_bar"],
		diam_m            = pr["diam_m"],
		safety_factor     = pr["safety_factor"],
		yield_factor_pa   = pr["yield_factor_pa"],
		wall_density_kgm3 = pr["wall_density_kgm3"],
		ullage_fraction   = pr.get("ullage_fraction", 0.0),
	)

	c_in = InjectorConfig(**data["injector"])

	c_fu = FuelConfig(**data["fuel"])

	c_nz = NozzleConfig(**data["nozzle"])

	c_op = OptimizationSeedConfig(**data["optimization"])

	return RocketConfig(
		cfg_global     = c_gl,
		cfg_oxy_tank   = c_ox,
		cfg_press_tank = c_pr,
		cfg_injector   = c_in,
		cfg_fuel       = c_fu,
		cfg_nozzle     = c_nz,
		cfg_optim      = c_op,
	)

def load_reactants(path: str | Path) -> MixtureConfig:
	with open(path, "rb") as f:
		data = tomllib.load(f)

	def parse_entry(r: dict) -> ReactantConfig:
		return ReactantConfig(
			name           = r["name"],
			reactype       = r["reactype"],
			formula_parts  = list(r["formula_parts"]),
			mass_fraction  = r.get("mass_fraction", 100.0),
			temperature_k  = r.get("temperature_k", 298.15),
			enthalpy       = r.get("enthalpy"),
			enthalpy_units = r.get("enthalpy_units"),
			density        = r.get("density"),
			density_units  = r.get("density_units"),
		)

	fuels = list(parse_entry(r) for r in data["fuel"])
	oxids = list(parse_entry(r) for r in data["oxid"])
	return MixtureConfig(fuels=fuels, oxidizers=oxids)
