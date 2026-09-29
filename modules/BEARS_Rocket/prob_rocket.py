#region Imports
import openmdao.api as om

from rocketcea.cea_obj import CEA_Obj
from openmdao.api      import Problem

from ..BEARS_Atmo  import BEARS_Atm
from .group_rocket import RocketGroup
#endregion

class RocketLaunchProblem(Problem):

	def __init__(
		self,
		atm           : BEARS_Atm,
		cea           : CEA_Obj,
		rho_ox        : float = 750.0,
		rho_fuel      : float = 900.0,
		target_apogee : float = 3100.0,
		**kwargs,
	):
		super().__init__(**kwargs)

		self.model = RocketGroup(
			atm=atm,
			cea=cea,
			rho_ox=rho_ox,
			rho_fuel=rho_fuel,
		)

		self.driver = om.ScipyOptimizeDriver()
		self.driver.options["optimizer"] = "SLSQP"

		self.model.add_design_var(
			"OptimizationVars.o_propellant_mass",
			lower=1.0,
			upper=50.0,
			ref=10.0,
		)

		self.model.add_constraint(
			"apogee",
			lower=target_apogee,
			ref=target_apogee,
		)

		self.model.add_objective(
			"OptimizationVars.o_propellant_mass",
			ref=10.0,
		)

	def setup(self, **kwargs):
		super().setup(**kwargs)

		# Vehicle parameters
		self.set_val("DesignVars.g_payload_mass",          1.0)
		self.set_val("DesignVars.g_diameter",              0.12)
		self.set_val("DesignVars.tank_pressure",           70)
		self.set_val("DesignVars.tank_diam",               0.12)
		self.set_val("DesignVars.injector_area",           1.5e-5)
		self.set_val("DesignVars.injector_cd",             0.7)
		self.set_val("DesignVars.fuel_port_diam",          0.05)
		self.set_val("DesignVars.fuel_reg_exponent",       0.5)
		self.set_val("DesignVars.fuel_reg_ref",            1.0e-4)
		self.set_val("DesignVars.nozzle_expansion_ratio",  40.0)
		self.set_val("DesignVars.nozzle_throat_area",      2.0e-4)

		# Starting point for optimization
		self.set_val("OptimizationVars.o_propellant_mass", 15.0)
		self.set_val("OptimizationVars.o_mixture_ratio",   6.0)

		return self

	def run(self):

		self.run_driver()

		bar_to_pa = 1e5

		return {
			"m_prop_kg":     self.get_val("OptimizationVars.o_propellant_mass")[0],
			"mr":            self.get_val("OptimizationVars.o_mixture_ratio")[0],
			"apogee_m":      self.get_val("apogee")[0],
			"burn_time_s":   self.get_val("burn_time")[0],
			"thrust_N":      self.get_val("Propulsion.prop_thrust")[0],
			"isp_s":         self.get_val("Propulsion.prop_isp")[0],
			"p_chamber_bar": self.get_val("Propulsion.prop_chamber_pressure")[0] / bar_to_pa,
			"m_dry_kg":      self.get_val("Mass.dry_mass")[0],
			"m_initial_kg":  self.get_val("Mass.initial_mass")[0],
		}
