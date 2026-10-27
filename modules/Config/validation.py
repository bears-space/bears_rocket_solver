#region Imports
from .records import RocketConfig, BipropellantConfig, SpeciesConfig
#endregion

class ConfigValidationError(ValueError):
	"""Raised when config values violate physical constraints"""
	pass

def validate_species_config(
	sp      : SpeciesConfig,
	context : str = "",
) -> list[str]:
	errors = []
	prefix = f"{context}: " if context else ""

	if not sp.name or not sp.name.strip():
		errors.append(f"{prefix}species name cannot be empty")

	if sp.mass_fraction <= 0:
		errors.append(f"{prefix}mass_fraction must be > 0 (got {sp.mass_fraction})")

	if sp.temperature_k <= 0:
		errors.append(f"{prefix}density must be > 0 (got {sp.get_density_si()})")

	return errors

def validate_bipropellant_config(cfg: BipropellantConfig) -> None:
	errors = []

	if not cfg.fuels:
		errors.append("fuels list cannot be empty")

	if not cfg.oxidizers:
		errors.append("oxidizers list cannot be empty")

	for f in cfg.fuels:
		errors.extend(validate_species_config(f, f"Fuel '{f.name}'"))

	for o in cfg.fuels:
		errors.extend(validate_species_config(o, f"Oxidizer '{o.name}'"))

	if errors:
		raise ConfigValidationError(
			"Invalid BipropellantConfig:\n  - " + "\n  - ".join(errors)
		)

def validate_rocket_config(cfg: RocketConfig) -> None:
	errors = []
	gl = cfg.cfg_global
	ox = cfg.cfg_oxy_tank
	pr = cfg.cfg_press_tank

	if gl.diameter_m <= 0:
		errors.append(f"global.diameter_m must be > 0 (got {gl.diameter_m})")

	if gl.clearance_m < 0:
		errors.append(f"global.clearance_m must be >= 0 (got {gl.clearance_m})")

	if ox.diam_m + 2 * gl.clearance_m > gl.diameter_m:
		errors.append(
			f"oxidizer_tank diameter ({ox.diam_m} m)"
			f" + clearance ({2 * gl.clearance_m} m) "
			f"exceeds airframe diameter ({gl.diameter_m} m)"
		)

	if pr.diam_m + 2 * gl.clearance_m > gl.diameter_m:
		errors.append(
			f"pressurant_tank diameter ({pr.diam_m} m)"
			f" + clearance ({2 * gl.clearance_m} m) "
			f"exceeds airframe diameter ({gl.diameter_m} m)"
		)

	# Pressure hierarchy
	if pr.pressure_bar <= ox.pressure_bar:
		errors.append(
			f"pressurant pressure ({pr.pressure_bar} bar) must exceed "
			f"oxidizer pressure ({ox.pressure_bar} bar)"
		)

	if ox.pressure_bar <= 0:
		errors.append(f"oxidizer_tank.pressure_bar must be > 0 (got {ox.pressure_bar})")

	if ox.safety_factor < 1.0 or pr.safety_factor < 1.0:
		errors.append(f"tank safety factors must be >= 1.0")

	if not (0.0 <= ox.ullage_fraction < 1.0):
		errors.append("oxidizer_tank.ullage_fraction must be in [0.0, 1.0)")

	# Engine and nozzle
	inj = cfg.cfg_injector
	nz  = cfg.cfg_nozzle

	if inj.area_m2 <= 0 or not (0.0 < inj.cd <= 1.0):
		errors.append("invalid injector geometry or discharge coefficient")

	if nz.throat_area_m2 <= 0 or nz.expansion_ratio <= 1.0:
		errors.append("invalid nozzle throat area or expansion ratio")

	if errors:
		raise ConfigValidationError(
			"Invalid RocketConfig:\n  - " + "\n  - ".join(errors)
		)
