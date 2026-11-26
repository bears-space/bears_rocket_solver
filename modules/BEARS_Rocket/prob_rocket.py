#region Imports
from typing import Any, Self

import openmdao.api as om
from openmdao.api import Problem

from ..BEARS_Atmo   import BEARS_Atm
from ..BEARS_Chem   import BEARS_Chem
from ..BEARS_Thermo import PressurantThermoModel
from ..Config       import (
	CONSTANTS,
	ChecksConfig,
	Gas,
	RocketConfig,
	Wall,
)

from .group_rocket import RocketGroup
from .reporting    import write_graphs, write_output_table
from .checks       import ROCKET_CHECKS, CheckResult, run_checks
#endregion

g = CONSTANTS.universal.standard_gravity  # Standard gravity [m/s^2]

OUTPUT_TABLE = "outputs/rocket.txt"  # All model variables after the run
GRAPH_DIR    = "figures"             # Model connectivity graphs
GRAPH_PREFIX = "rocket"

class RocketLaunchProblem(Problem):
	"""
	Least propellant that meets apogee, thrust and chamber pressure targets

	The design variables, their bounds and the constraint limits all come
	from the rocket inputs. The `ref` values only scale the problem for the
	optimizer
	"""

	def __init__(
		self,
		cfg          : RocketConfig,           # Rocket design inputs
		limits       : ChecksConfig,           # Check acceptance limits
		atm          : BEARS_Atm,              # Atmosphere model
		chem         : BEARS_Chem,             # Propellant chemistry
		ox_wall      : Wall,                   # Oxidizer tank wall layup
		press_wall   : Wall,                   # Pressurant bottle layup
		press_gas    : Gas,                    # Pressurant gas
		press_thermo : PressurantThermoModel,  # Blowdown model
		**kwargs     : Any,                    # Passed to openmdao Problem
	) -> None:
		super().__init__(
			model = RocketGroup(
				cfg          = cfg,
				chem         = chem,
				atm          = atm,
				ox_wall      = ox_wall,
				press_wall   = press_wall,
				press_gas    = press_gas,
				press_thermo = press_thermo,
			),
			**kwargs,
		)
		self.cfg    = cfg
		self.limits = limits

		self.driver = om.ScipyOptimizeDriver()
		self.driver.options["optimizer"] = "SLSQP"

		gl = cfg.cfg_global
		op = cfg.cfg_optim
		co = cfg.cfg_constraints

		#region Design variables
		self.model.add_design_var(
			"OptimizationVars.o_propellant_mass",
			lower = op.propellant_mass_kg.lower,
			upper = op.propellant_mass_kg.upper,
			units = "kg",
			ref   = 5.0,
		)

		self.model.add_design_var(
			"OptimizationVars.o_mixture_ratio",
			lower = op.mixture_ratio.lower,
			upper = op.mixture_ratio.upper,
			ref   = 6.0,
		)

		self.model.add_design_var(
			"OptimizationVars.o_injector_area",
			lower = op.injector_area_m2.lower,
			upper = op.injector_area_m2.upper,
			units = "m**2",
			ref   = 1.5e-5,
		)

		# Fixed nozzle exit: throat area sets the expansion ratio
		self.model.add_design_var(
			"OptimizationVars.o_nozzle_throat_area",
			lower = op.nozzle_throat_area_m2.lower,
			upper = op.nozzle_throat_area_m2.upper,
			units = "m**2",
			ref   = 5.0e-4,
		)
		#endregion

		#region Constraints
		# The 1D apogee has to cover the trajectory losses
		eff_apogee = gl.target_altitude_m / cfg.cfg_efficiencies.trajectory
		self.model.add_constraint(
			"apogee", lower=eff_apogee, ref=eff_apogee, units="m",
		)

		# Thrust and apogee fix burn time, so it only needs an upper cap
		self.model.add_constraint(
			"burn_time",
			upper = co.max_burn_time_s,
			ref   = 6.0,
			units = "s",
		)

		# Engine is sized to target thrust at target chamber pressure
		self.model.add_constraint(
			"Propulsion.prop_thrust",
			equals = gl.target_thrust_N,
			ref    = gl.target_thrust_N,
			units  = "N",
		)

		self.model.add_constraint(
			"Propulsion.prop_chamber_pressure",
			equals = gl.target_chamber_pressure_bar,
			ref    = gl.target_chamber_pressure_bar,
			units  = "bar",
		)

		self.model.add_constraint(
			"Propulsion.injector_delta_p",
			lower = co.min_injector_pressure_drop_bar,
			ref   = co.min_injector_pressure_drop_bar,
			units = "bar",
		)

		# The fuel grain has to fit inside the airframe bore
		self.model.add_constraint(
			"EngineFit.grain_margin", lower=0.0, ref=0.01, units="m",
		)
		#endregion

		self.model.add_objective(
			"OptimizationVars.o_propellant_mass", ref=10.0,
		)

	def run(self) -> Self:
		self.run_driver()
		return self

	def verify(self) -> tuple[CheckResult, ...]:
		"""Check optimized rocket against limits, raising on errors"""
		return run_checks(self, ROCKET_CHECKS)

	#region Outputs
	def print_summary(self) -> None:
		FMT = "8.3f"

		self.verify()

		gv = self.get_val
		m_prop = gv("OptimizationVars.o_propellant_mass",    units="kg")[0]
		m_ld   = gv("Mass.prop_loaded_mass",                 units="kg")[0]
		a_inj  = gv("OptimizationVars.o_injector_area",      units="mm**2")[0]
		a_thr  = gv("OptimizationVars.o_nozzle_throat_area", units="cm**2")[0]
		d_ex   = gv("DesignVars.nozzle_exit_diam",           units="mm")[0]
		eps    = gv("Propulsion.nozzle_expansion_ratio")[0]
		m_ex   = gv("Propulsion.nozzle_exit_mach")[0]
		mr     = gv("OptimizationVars.o_mixture_ratio")[0]
		ap     = gv("apogee",                                units="m")[0]
		t_burn = gv("burn_time",                             units="s")[0]
		thr    = gv("Propulsion.prop_thrust",                units="N")[0]
		isp    = gv("Propulsion.prop_isp",                   units="s")[0]
		pch    = gv("Propulsion.prop_chamber_pressure",      units="bar")[0]
		tch    = gv("Propulsion.prop_chamber_temp",          units="K")[0]
		dp     = gv("Propulsion.injector_delta_p",           units="bar")[0]
		mdry   = gv("Mass.dry_mass",                         units="kg")[0]
		mpr    = gv("Mass.pressurant_mass",                  units="kg")[0]
		mi     = gv("Mass.initial_mass",                     units="kg")[0]
		twr    = thr / (mi * g)

		print("Optimized rocket parameters:")
		print("")
		print(f"Burned (optimized) m_prop:\t{m_prop:{FMT}} kg")
		print(f"Loaded m_prop:            \t{m_ld:{FMT}} kg")
		print(f"Optimized A_inj:          \t{a_inj:{FMT}} mm²")
		print(f"Optimized A_throat:       \t{a_thr:{FMT}} cm²")
		print(f"Optimized MR:             \t{mr:{FMT}}")
		print(f"Nozzle exit diameter:     \t{d_ex:{FMT}} mm")
		print(f"Expansion ratio:          \t{eps:{FMT}}")
		print("")
		print(f"Apogee:                   \t{ap:{FMT}} m")
		print(f"Burn time:                \t{t_burn:{FMT}} s")
		print(f"Liftoff thrust:           \t{thr:{FMT}} N")
		print(f"Liftoff Isp:              \t{isp:{FMT}} s")
		print(f"Chamber pressure:         \t{pch:{FMT}} bar")
		print(f"Chamber flame temp:       \t{tch:{FMT}} K")
		print(f"Injector ΔP:              \t{dp:{FMT}} bar")
		print(f"Nozzle exit Mach:         \t{m_ex:{FMT}}")
		print("")
		print(f"Dry mass:                 \t{mdry:{FMT}} kg")
		print(f"Pressurant mass:          \t{mpr:{FMT}} kg")
		print(f"Total mass at liftoff:    \t{mi:{FMT}} kg")
		print(f"TWR at launch:            \t{twr:{FMT}}")

	def report(self) -> None:
		"""Print results, write every variable to a file and draw graphs"""
		self.print_summary()
		write_output_table(self.model, OUTPUT_TABLE)
		write_graphs(self.model, GRAPH_DIR, GRAPH_PREFIX)
	#endregion
