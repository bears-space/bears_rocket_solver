#region Imports
from dataclasses import dataclass
#endregion

#region Design
@dataclass(frozen=True)
class GlobalConfig:
	payload_mass_kg         : float # [kg]
	target_altitude_m       : float # [m]
	diameter_m              : float # [m]
	clearance_m             : float # [m]

@dataclass(frozen=True)
class TankConfig:
	pressure_bar            : float # [bar]
	diam_m                  : float # [m]
	safety_factor           : float
	yield_factor_pa         : float # [Pa]
	wall_density_kgm3       : float # [kg/m^3]
	ullage_fraction         : float = 0.0

@dataclass(frozen=True)
class InjectorConfig:
	area_m2                 : float # [m^2]
	cd                      : float

@dataclass(frozen=True)
class FuelConfig:
	port_diam_m             : float # [m]
	reg_exponent            : float
	reg_ref_ms              : float # [m/s]
	oxy_mass_flux_ref_kgm2s : float # [kg/(m^2*s)]

@dataclass(frozen=True)
class NozzleConfig:
	throat_area_m2          : float # [m^2]
	expansion_ratio         : float
	length_m                : float # [m]
	eta_friction            : float

@dataclass(frozen=True)
class OptimizationSeedConfig:
	propellant_mass_kg      : float # [kg]
	mixture_ratio           : float
	injector_area_m2        : float # [m^2]
	nozzle_throat_area_m2   : float # [m^2]
#endregion

#region Chemistry
@dataclass(frozen=True)
class ReactantConfig:
	name                    : str
	reactype                : str # "fuel" or "oxid"
	formula_parts           : list[dict[str, float]]
	mass_fraction           : float = 100.0
	temperature_k           : float = 298.15
	enthalpy                : float | None = None
	enthalpy_units          : str   | None = None
	density                 : float | None = None
	density_units           : str   | None = None

	def get_density_si(self) -> float:
		if self.density is None:
			return 1000.0

		if self.density_units in ("g/cm^3", "g/cc", "g/cm3"):
			return self.density * 1000.0

		return self.density

@dataclass(frozen=True)
class MixtureConfig:
	fuels                   : list[ReactantConfig]
	oxidizers               : list[ReactantConfig]
#endregion

#region Master specification
@dataclass(frozen=True)
class RocketConfig:
	cfg_global      : GlobalConfig
	cfg_oxy_tank    : TankConfig
	cfg_press_tank  : TankConfig
	cfg_injector    : InjectorConfig
	cfg_fuel        : FuelConfig
	cfg_nozzle      : NozzleConfig
	cfg_optim       : OptimizationSeedConfig
#endregion
