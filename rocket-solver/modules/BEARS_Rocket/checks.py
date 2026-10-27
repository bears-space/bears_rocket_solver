#region Imports
from openmdao.api import Problem

from typing import Callable, Literal, NamedTuple
from scipy.constants import g
#endregion

#region Types
class CheckResult(NamedTuple):
	severity : Literal["error", "warning"]
	message  : str

CheckFn = Callable[[Problem], tuple[CheckResult, ...]]
#endregion

#region Flight Checks
def check_injector_dp(prob: Problem) -> tuple[CheckResult, ...]:
	issues: list[CheckResult] = []
	dp = prob.get_val("Propulsion.injector_delta_p",      units="bar")[0]
	pc = prob.get_val("Propulsion.prop_chamber_pressure", units="bar")[0]

	if dp <= 0.0:
		issues.append(CheckResult(
			"error",
			f"Injector ΔP non-positive ({dp:.3f} bar)"
		))
	elif dp / pc < 0.15:
		ratio = dp / pc
		issues.append(CheckResult(
			"warning",
			f"Injector ΔP ratio low ({ratio:.1%})"
		))

	return tuple(issues)

def check_liftoff_twr(prob: Problem) -> tuple[CheckResult, ...]:
	issues: list[CheckResult] = []
	thr = prob.get_val("Propulsion.prop_thrust", units="N")[0]
	mi  = prob.get_val("Mass.initial_mass",      units="kg")[0]
	twr = thr / (mi * g)

	if twr < 1.0:
		issues.append(CheckResult(
			"error",
			f"Liftoff TWR below 1.0 ({twr:.3f})"
		))
	elif twr < 1.3:
		issues.append(CheckResult(
			"warning",
			f"Liftoff TWR is low ({twr:.3f})"
		))

	return tuple(issues)

def check_mass_balance(prob: Problem) -> tuple[CheckResult, ...]:
	mi    = prob.get_val("Mass.initial_mass",                  units="kg")[0]
	mdry  = prob.get_val("Mass.dry_mass",                      units="kg")[0]
	mprop = prob.get_val("OptimizationVars.o_propellant_mass", units="kg")[0]
	mpr   = prob.get_val("Mass.pressurant_mass",               units="kg")[0]

	try:
		mprop = prob.get_val("Mass.loaded_prop_mass", units="kg")[0]
	except KeyError:
		pass

	mcalc = mdry + mprop + mpr

	if abs(mi - mcalc) > 1e-3:
		return (CheckResult(
			"error",
			f"Mass balance mismatch: {mi:.3f} kg != {mcalc:.3f} kg"
		),)
	
	return ()

def check_target_apogee(prob: Problem) -> tuple[CheckResult, ...]:
	ap     = prob.get_val("apogee",                       units="m")[0]
	target = prob.get_val("DesignVars.g_target_altitude", units="m")[0]

	err = abs(ap - target)

	if err > 20.0:
		return (CheckResult(
			"error",
			f"Apogee target error is {res['apogee_error_m']:.2f} m"
		),)

	return ()

def check_combustion_isp(prob: Problem) -> tuple[CheckResult, ...]:
	from .prob_rocket    import RocketLaunchProblem
	from .prob_teststand import TestStandProblem

	match prob:
		case RocketLaunchProblem():
			isp = prob.get_val("Propulsion.prop_isp", units="s")[0]
		case TestStandProblem():
			isp = prob.get_val("test_isp", units="s")[0]
		case _:
			raise TypeError(f"Unsupported problem: {type(prob).__name__}")

	if not (150.0 <= isp <= 350.0):
		return (CheckResult(
			"warning",
			f"Isp ({isp:.1f} s) outside range [150, 350]"
		))

	return ()
#endregion

#region Test Stand Checks
def check_feed_dp(prob: Problem) -> tuple[CheckResult, ...]:
	issues: list[CheckResult] = []
	pt2 = prob.get_val("Sensors.PT2_run_tank_pressure", units="bar")[0]
	pt3 = prob.get_val("test_chamber_pressure_PT3",     units="bar")[0]

	dp = pt2 - pt3

	if dp <= 0.0:
		issues.append(CheckResult(
			"error",
			f"Feed ΔP non-positive ({dp:.3f} bar)"
		))
	elif dp / pt3 < 0.15:
		ratio = dp / pt3
		issues.append(CheckResult(
			"warning",
			f"Feed ΔP ratio is low ({ratio:.1%})"
		))

	return tuple(issues)

def check_teststand_thrust(prob: Problem) -> tuple[CheckResult, ...]:
	thrust = prob.get_val("test_thrust", units="N")[0]

	if thrust <= 0.0:
		return (CheckResult(
			"error",
			f"Thrust non-positive ({res['thrust_N']:.3f} N)"
		))

	return ()

def check_supply_pressure_hierarchy(prob: Problem) -> tuple[CheckResult, ...]:
	pt2 = prob.get_val("Sensors.PT2_run_tank_pressure", units="bar")[0]
	pt4 = 200.0

	if pt4 < pt2:
		return (CheckResult(
			"error",
			"N2 supply pressure PT4 is below run tank pressure PT2"
		))

	return ()

def check_flame_temperature(prob: Problem) -> tuple[CheckResult, ...]:
	from .prob_rocket    import RocketLaunchProblem
	from .prob_teststand import TestStandProblem

	match prob:
		case RocketLaunchProblem():
			tc = prob.get_val("Propulsion.prop_chamber_temp", units="K")[0]
		case TestStandProblem():
			tc = prob.get_val("test_chamber_temp_TC3", units="K")[0]
		case _:
			raise TypeError(f"Unsupported problem: {type(prob).__name__}")

	if not (1500.0 <= tc <= 4000.0):
		return (CheckResult(
			"warning",
			f"TC3 flame temp ({tc:.3f} K) outside range [1500, 4000]"
		))

	return ()
#endregion

#region Suites and Runner
DEFAULT_ROCKET_CHECKS: tuple[CheckFn, ...] = (
	check_injector_dp,
	check_liftoff_twr,
	check_mass_balance,
	check_target_apogee,
	check_combustion_isp,
)

DEFAULT_TESTSTAND_CHECKS: tuple[CheckFn, ...] = (
	check_feed_dp,
	check_teststand_thrust,
	check_combustion_isp,
	check_supply_pressure_hierarchy,
	check_flame_temperature,
)

def run_checks(
	prob           : Problem,
	checks         : tuple[CheckFn, ...],
	raise_on_error : bool = True,
) -> tuple[CheckResult, ...]:
	results: list[CheckResult] = []
	for check in checks:
		out = check(prob)
		if isinstance(out, CheckResult):
			results.append(out)
		else:
			results.extend(out)

	errors   = [r.message for r in results if r.severity == "error"]
	warnings = [r.message for r in results if r.severity == "warning"]

	if raise_on_error and errors:
		msg = "\n  - ".join(errors)
		raise ValueError(f"Run verification failed:\n  - {msg}")

	for w in warnings:
		print(f"Warning: {w}")

	return tuple(results)
#endregion
