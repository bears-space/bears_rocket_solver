#region Imports
import openmdao.api as om

from rocketcea.cea_obj import CEA_Obj
from openmdao.api      import Problem

from .group_teststand import TestStandGroup
#endregion

class TestStandProblem(Problem):

	def __init__(
		self,
		cea      : CEA_Obj,
		rho_ox   : float = 750.0,
		rho_fuel : float = 900.0,
		**kwargs,
	):
		super().__init__(**kwargs)

		self.cea = cea
		self.model = TestStandGroup(
			cea=cea,
			rho_ox=rho_ox,
			rho_fuel=rho_fuel,
		)

	def setup(self, **kwargs):
		super().setup(**kwargs)

		# Run tank
		self.set_val("run_tank_pressure_PT2", 60.0,   units="bar")
		self.set_val("run_tank_diam",         0.15,   units="m")
		self.set_val("run_tank_ullage_frac",  0.08)
		self.set_val("run_tank_wall_density", 2700.0, units="kg/m**3")
		self.set_val("run_tank_yield_factor", 276e6,  units="Pa")
		self.set_val("run_tank_fluid_mass",   10.0,   units="kg")

		# Engine baseline parameters
		self.set_val("test_prop_mass_init",   8.0,    units="kg")
		self.set_val("test_mixture_ratio",    6.618)
		self.set_val("injector_area",         1.5e-5, units="m**2")
		self.set_val("injector_cd",           0.70)
		self.set_val("fuel_port_diam",        0.05,   units="m")
		self.set_val("fuel_reg_exponent",     0.50)
		self.set_val("fuel_reg_ref",          1.0e-4, units="m/s")
		self.set_val("nozzle_throat_area",    2.0e-4, units="m**2")
		self.set_val("nozzle_length",         0.15,   units="m")
		self.set_val("nozzle_eta_friction",   0.95)

		return self

	def set_opt_vars(
		self,
		m_prop_kg    : float | None = None,
		mr           : float | None = None,
		a_inj_mm2    : float | None = None,
		a_throat_cm2 : float | None = None,
	):
		if m_prop_kg is not None:
			self.set_val("test_prop_mass_init", m_prop_kg,    units="kg")
		if mr is not None:
			self.set_val("test_mixture_ratio",  mr)
		if a_inj_mm2 is not None:
			self.set_val("injector_area",       a_inj_mm2,    units="mm**2")
		if a_throat_cm2 is not None:
			self.set_val("nozzle_throat_area",  a_throat_cm2, units="cm**2")

	def run(self):

		self.run_model()

		pt2    = self.get_val("run_tank_pressure_PT2",     units="bar")[0]
		pt3    = self.get_val("test_chamber_pressure_PT3", units="bar")[0]
		thrust = self.get_val("test_thrust",               units="N")[0]
		isp    = self.get_val("test_isp",                  units="s")[0]

		pa_to_psia = 1.450377e-4
		bar_to_pa  = 1e5

		pc_psia = pt3 * bar_to_pa * pa_to_psia
		mr      = self.get_val("test_mixture_ratio")[0]
		tc3_k   = self.cea.get_Tcomb(Pc=pc_psia, MR=mr) * (5.0 / 9.0)

		return {
			"PT1_N2O_supply_bar": 65.0,
			"TC1_N2O_supply_K":   288.15,
			"PT2_run_tank_bar":   pt2,
			"TC2_run_liquid_K":   275.15,
			"PT3_chamber_bar":    pt3,
			"TC3_chamber_temp_K": tc3_k,
			"PT4_N2_supply_bar":  200.0,
			"TC4_run_dome_K":     285.15,
			"delta_p_feed_bar":   pt2 - pt3,
			"thrust_N":           thrust,
			"isp_s":              isp,
		}
