#region Imports
from typing import Any, Callable, Literal, NamedTuple

from .results import RocketResult, TestStandResult
#endregion

#region Types
class CheckResult(NamedTuple):
	severity : Literal["error", "warning"]
	message  : str

CheckFn = Callable[[Any], tuple[CheckResult, ...]]
#endregion

#region Flight Checks
def check_injector_dp(res: RocketResult) -> tuple[CheckResult, ...]:
	issues: list[CheckResult] = []
	dp = res.injector.delta_p_bar
	pc = res.propulsion.p_chamber_bar

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

def check_liftoff_twr(res: RocketResult) -> tuple[CheckResult, ...]:
	issues: list[CheckResult] = []
	twr = res.trajectory.twr_launch

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

def check_mass_balance(res: RocketResult) -> tuple[CheckResult, ...]:
	mi = res.mass.initial_kg
	mc = res.mass.calculated_kg

	if abs(mi - mc) > 1e-3:
		return (CheckResult(
			"error",
			f"Mass balance mismatch: {mi:.3f} kg != {mc:.3f} kg"
		))
	
	return ()

def check_target_apogee(res: RocketResult) -> tuple[CheckResult, ...]:
	err = res.trajectory.apogee_error_m

	if err > 20.0:
		return (CheckResult(
			"error",
			f"Apogee target error is {res['apogee_error_m']:.2f} m"
		))

	return ()

def check_combustion_isp(
	res: RocketResult | TestStandResult,
) -> tuple[CheckResult, ...]:
	isp = res.propulsion.isp_s

	if not (150.0 <= isp <= 350.0):
		return (CheckResult(
			"warning",
			f"Isp ({res['isp_s']:.1f} s) outside range [150, 350]"
		))

	return ()
#endregion

#region Test Stand Checks
def check_feed_dp(res: TestStandResult) -> tuple[CheckResult, ...]:
	issues: list[CheckResult] = []
	dp = res.sensors.delta_p_feed_bar
	pc = res.sensors.PT3_chamber_bar

	if dp <= 0.0:
		issues.append(CheckResult(
			"error",
			f"Feed ΔP non-positive ({dp:.3f} bar)"
		))
	elif dp / pc < 0.15:
		ratio = dp / pc
		issues.append(CheckResult(
			"warning",
			f"Feed ΔP ratio is low ({ratio:.1%})"
		))

	return tuple(issues)

def check_teststand_thrust(res: TestStandResult) -> tuple[CheckResult, ...]:
	if res.propulsion.thrust_N <= 0.0:
		return (CheckResult(
			"error",
			f"Thrust non-positive ({res['thrust_N']:.3f} N)"
		))

	return ()

def check_supply_pressure_hierarchy(
	res: TestStandResult,
) -> tuple[CheckResult, ...]:
	if res.sensors.PT4_N2_supply_bar < res.sensors.PT2_run_tank_bar:
		return (CheckResult(
			"error",
			"N2 supply pressure PT4 is below run tank pressure PT2"
		))

	return ()

def check_flame_temperature(res: TestStandResult) -> tuple[CheckResult, ...]:
	tc = res.sensors.TC3_chamber_temp_K

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
	res            : dict,
	checks         : tuple[CheckFn, ...],
	raise_on_error : bool = True,
) -> tuple[CheckResult, ...]:
	results: list[CheckResult] = []
	for check in checks:
		results.extend(check(res))

	errors   = [r.message for r in results if r.severity == "error"]
	warnings = [r.message for r in results if r.severity == "warning"]

	if raise_on_error and errors:
		msg = "\n  - ".join(errors)
		raise ValueError(f"Run verification failed:\n  - {msg}")

	for w in warnings:
		print(f"Warning: {w}")

	return tuple(results)
#endregion
