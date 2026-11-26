"""
Acceptance checks of the optimized rocket

Each check reads the run results and the limits from the checks file, and
returns its findings. Errors stop the run, warnings are printed
"""

#region Imports
from typing       import Callable, Literal, NamedTuple
from openmdao.api import Problem

from ..Config import CONSTANTS
#endregion

g = CONSTANTS.universal.standard_gravity  # Standard gravity [m/s^2]

#region Types
class CheckResult(NamedTuple):
	# Errors stop the run, warnings are printed
	severity : Literal["error", "warning"]
	message  : str  # What is wrong, with the values

CheckFn = Callable[[Problem], tuple[CheckResult, ...]]
#endregion

#region Checks
def check_injector_pressure_drop(prob: Problem) -> tuple[CheckResult, ...]:
	"""Injector needs enough pressure drop to decouple feed from chamber"""
	dp = prob.get_val("Propulsion.injector_delta_p",      units="bar")[0]
	pc = prob.get_val("Propulsion.prop_chamber_pressure", units="bar")[0]

	if dp <= 0.0:
		msg = f"Injector ΔP non-positive ({dp:.3f} bar)"
		return (CheckResult("error", msg),)
	if dp / pc < prob.limits.min_injector_pressure_drop_ratio:
		msg = f"Injector ΔP ratio low ({dp / pc:.1%})"
		return (CheckResult("warning", msg),)
	return ()

def check_liftoff_twr(prob: Problem) -> tuple[CheckResult, ...]:
	"""The rocket has to leave the rail with a thrust-to-weight margin"""
	limits = prob.limits
	thr = prob.get_val("Propulsion.prop_thrust", units="N")[0]
	mi  = prob.get_val("Mass.initial_mass",      units="kg")[0]
	twr = thr / (mi * g)

	if twr < limits.min_liftoff_twr:
		msg = f"Liftoff TWR below {limits.min_liftoff_twr} ({twr:.3f})"
		return (CheckResult("error", msg),)
	if twr < limits.low_liftoff_twr:
		msg = f"Liftoff TWR is low ({twr:.3f})"
		return (CheckResult("warning", msg),)
	return ()

def check_fuel_grain_diameter(prob: Problem) -> tuple[CheckResult, ...]:
	"""The fuel grain has to fit the airframe bore"""
	d_grain = prob.get_val("Propulsion.fuel_grain_diam",  units="m")[0]
	d_bore  = prob.get_val("DesignVars.g_inner_diameter", units="m")[0]

	if d_grain > d_bore:
		return (CheckResult(
			"error",
			f"Fuel grain diameter ({d_grain * 1e3:.1f} mm) is larger than "
			f"the rocket inner diameter ({d_bore * 1e3:.1f} mm)",
		),)
	return ()

def check_engine_targets(prob: Problem) -> tuple[CheckResult, ...]:
	"""Optimized engine must deliver target thrust and chamber pressure"""
	tolerance = prob.limits.target_tolerance
	targets = (
		(
			"Thrust",
			"Propulsion.prop_thrust",
			"DesignVars.g_target_thrust",
			"N",
		),
		(
			"Chamber pressure",
			"Propulsion.prop_chamber_pressure",
			"DesignVars.g_target_chamber_pressure",
			"bar",
		),
	)

	issues: list[CheckResult] = []
	for label, name, target_name, units in targets:
		val    = prob.get_val(name,        units=units)[0]
		target = prob.get_val(target_name, units=units)[0]
		if abs(val - target) > tolerance * target:
			issues.append(CheckResult(
				"error",
				f"{label} ({val:.3f} {units}) misses its target "
				f"({target:.3f} {units})",
			))
	return tuple(issues)

def check_target_apogee(prob: Problem) -> tuple[CheckResult, ...]:
	"""The apogee, after trajectory losses, has to hit its target"""
	ap     = prob.get_val("Trajectory.apogee",            units="m")[0]
	target = prob.get_val("DesignVars.g_target_altitude", units="m")[0]
	eta_t  = prob.get_val("EfficiencyVars.eta_trajectory")[0]

	err = abs(ap * eta_t - target)
	if err > prob.limits.apogee_tolerance_m:
		return (CheckResult("error", f"Apogee target error is {err:.2f} m"),)
	return ()

def check_combustion_isp(prob: Problem) -> tuple[CheckResult, ...]:
	"""The delivered Isp has to be plausible for a hybrid"""
	limits = prob.limits
	isp = prob.get_val("Propulsion.prop_isp", units="s")[0]

	if not (limits.min_isp_s <= isp <= limits.max_isp_s):
		return (CheckResult(
			"warning",
			f"Isp ({isp:.1f} s) outside range "
			f"[{limits.min_isp_s}, {limits.max_isp_s}]",
		),)
	return ()

def check_flame_temperature(prob: Problem) -> tuple[CheckResult, ...]:
	"""The chamber temperature has to be plausible for the propellants"""
	limits = prob.limits
	tc = prob.get_val("Propulsion.prop_chamber_temp", units="K")[0]

	lo, hi = limits.min_flame_temperature_k, limits.max_flame_temperature_k
	if not (lo <= tc <= hi):
		return (CheckResult(
			"warning",
			f"Flame temperature ({tc:.3f} K) outside range [{lo}, {hi}]",
		),)
	return ()
#endregion

#region Suite and runner
ROCKET_CHECKS: tuple[CheckFn, ...] = (
	check_injector_pressure_drop,
	check_liftoff_twr,
	check_fuel_grain_diameter,
	check_engine_targets,
	check_target_apogee,
	check_combustion_isp,
	check_flame_temperature,
)

def run_checks(
	prob   : Problem,
	checks : tuple[CheckFn, ...],
) -> tuple[CheckResult, ...]:
	"""Run `checks`, print the warnings and raise on any error"""
	results = [result for check in checks for result in check(prob)]

	for r in results:
		if r.severity == "warning":
			print(f"Warning: {r.message}")

	errors = [r.message for r in results if r.severity == "error"]
	if errors:
		msg = "Run verification failed:\n  - " + "\n  - ".join(errors)
		raise ValueError(msg)

	return tuple(results)
#endregion
