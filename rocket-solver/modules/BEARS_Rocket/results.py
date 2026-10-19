#region Imports
from dataclasses import dataclass, field
from typing      import Any
#endregion

#region Component summaries
@dataclass(frozen=True)
class InjectorSummary:
	area_mm2    : float # [mm^2]
	delta_p_bar : float # [bar]

@dataclass(frozen=True)
class NozzleSummary:
	throat_area_cm2: float # [cm^2]

@dataclass(frozen=True)
class PropulsionSummary:
	thrust_N      : float # [N]
	isp_s         : float # [s]
	p_chamber_bar : float # [bar]
	mixture_ratio : float
	burn_time_s   : float = 0.0 # [s]

@dataclass(frozen=True)
class MassSummary:
	initial_kg    : float # [kg]
	dry_kg        : float # [kg]
	propellant_kg : float # [kg]
	pressurant_kg : float # [kg]
	calculated_kg : float # [kg]

@dataclass(frozen=True)
class TrajectorySummary:
	apogee_m       : float # [m]
	apogee_error_m : float # [m]
	twr_launch     : float

@dataclass(frozen=True)
class TestStandSensors:
	PT1_N2O_supply_bar : float # [bar]
	TC1_N2O_supply_K   : float # [K]
	PT2_run_tank_bar   : float # [bar]
	TC2_run_liquid_K   : float # [K]
	PT3_chamber_bar    : float # [bar]
	TC3_chamber_temp_K : float # [K]
	PT4_N2_supply_bar  : float # [bar]
	TC4_run_dome_K     : float # [K]
	delta_p_feed_bar   : float # [bar]
#endregion

#region Top-level results
@dataclass(frozen=True)
class RocketResult:
	propulsion : PropulsionSummary
	injector   : InjectorSummary
	nozzle     : NozzleSummary
	mass       : MassSummary
	trajectory : TrajectorySummary
	raw        : dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class TestStandResult:
	sensors    : TestStandSensors
	propulsion : PropulsionSummary
	raw        : dict[str, Any] = field(default_factory=dict)
#endregion
