#region Imports
from dataclasses import dataclass, field
#endregion

#region Design
@dataclass(frozen=True)
class GlobalConfig:
	payload_mass_kg         : float # [kg]
	nonprop_mass_kg         : float # [kg]
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
	boss_opening_m          : float = 0.02  # [m]
	boss_length_fwd_m       : float = 0.015 # [m]
	boss_length_aft_m       : float = 0.015 # [m]
	reg_margin_bar          : float = 20.0  # [bar]
	ambient_temp_c          : float = 30.0  # [deg C]

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
class IgniterConfig:
	burn_time_s           : float = 1.0    # [s]
	burn_rate_ms          : float = 0.0015 # [m/s]
	flame_spread_ms       : float = 0.15   # [m/s]
	max_spread_delay_s    : float = 0.10   # [s]
	thermite_density_kgm3 : float = 3800.0 # [kg/m^3]

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

@dataclass(frozen=True)
class EfficienciesConfig:
	combustion              : float # [kg]
	trajectory              : float
	propellant_utilization  : float # [m^2]
	regression_correction   : float # [m^2]
	nozzle_friction         : float # [m^2]
#endregion

#region Chemistry
@dataclass(frozen=True)
class SpeciesConfig:
	name                    : str
	formula_parts           : tuple[dict[str, float], ...] = ()
	mass_fraction           : float = 100.0
	temperature_k           : float = 298.15
	enthalpy                : float | None = None
	enthalpy_units          : str   | None = None
	density                 : float | None = None
	density_units           : str   | None = None
	role                    : str   | None = None

	def get_density_si(self) -> float:
		if self.density is None:
			return 1000.0

		if self.density_units in ("g/cm^3", "g/cc", "g/cm3"):
			return self.density * 1000.0

		return self.density

@dataclass(frozen=True)
class BipropellantConfig:
	fuels                   : tuple[SpeciesConfig, ...]
	oxidizers               : tuple[SpeciesConfig, ...]

@dataclass(frozen=True)
class MonopropellantConfig:
	species                 : tuple[SpeciesConfig, ...]

@dataclass(frozen=True)
class WorkingFluidConfig:
	species                 : tuple[SpeciesConfig, ...]

# Type alias for one of the above
PropellantConfig = (
	BipropellantConfig | MonopropellantConfig | WorkingFluidConfig
)
#endregion

#region Materials and Fluids
@dataclass(frozen=True)
class MaterialConfig:
	id                      : str
	name                    : str
	density                 : float
	yield_strength          : float
	ultimate_strength       : float
	elastic_modulus         : float

@dataclass(frozen=True)
class GasConfig:
	id                      : str
	name                    : str
	molar_mass              : float
	gamma                   : float
	z_factor                : float = 1.0

	@property
	def r_specific(self) -> float:
		return 8314.462618 / self.molar_mass

@dataclass(frozen=True)
class LayerConfig:
	material_id       : str
	thickness_m       : float | None = None # None for pressure-sized
	is_load_bearing   : bool  = True        # False for thermal insulation
	helical_angle_deg : float | None = None # None for isotropic or dynamic boss
	efficiency        : float = 0.85        # Fiber translation efficiency
	fiber_volume_frac : float = 0.72        # Fiber volume fraction

@dataclass(frozen=True)
class WallConfig:
	id                : str
	layers            : tuple[LayerConfig, ...]

@dataclass(frozen=True)
class MaterialsConfig:
	materials         : tuple[MaterialConfig, ...]
	walls             : tuple[WallConfig, ...]

@dataclass(frozen=True)
class FluidsConfig:
	gases             : tuple[GasConfig, ...]
#endregion

#region Master specification
@dataclass(frozen=True)
class RocketConfig:
	cfg_global        : GlobalConfig
	cfg_oxy_tank      : TankConfig
	cfg_press_tank    : TankConfig
	cfg_injector      : InjectorConfig
	cfg_fuel          : FuelConfig
	cfg_igniter       : IgniterConfig
	cfg_nozzle        : NozzleConfig
	cfg_optim         : OptimizationSeedConfig
	cfg_efficiencies  : EfficienciesConfig = (
		field(default_factory=EfficienciesConfig)
	)
#endregion
