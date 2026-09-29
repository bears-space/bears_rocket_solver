# region Imports
import openmdao.api as om

from openmdao.api      import Group, IndepVarComp
from rocketcea.cea_obj import CEA_Obj

from .comp_tank    import TankComponent
from .group_engine import HybridEngineGroup
# endregion

class TestStandGroup(Group):

	def initialize(self):
		self.options.declare("cea",                     types=CEA_Obj)
		self.options.declare("rho_ox",   default=750.0, types=float)
		self.options.declare("rho_fuel", default=900.0, types=float)

	def setup(self):
		cea      = self.options["cea"]
		rho_ox   = self.options["rho_ox"]
		rho_fuel = self.options["rho_fuel"]

		self.set_input_defaults("run_tank_pressure_PT2", val=60e5,   units="Pa")
		self.set_input_defaults("run_tank_density",      val=rho_ox, units="kg/m**3")
		self.set_input_defaults("run_tank_fluid_mass",   val=10.0,   units="kg")

		#region Sensors
		sensors = self.add_subsystem("Sensors", IndepVarComp())
		sensors.add_output("PT1_N2O_supply_pressure", val=65.0,   units="bar")
		sensors.add_output("TC1_N2O_supply_temp",     val=288.15, units="K")
		sensors.add_output("PT2_run_tank_pressure",   val=60.0,   units="bar")
		sensors.add_output("TC2_run_liquid_temp",     val=275.15, units="K")
		sensors.add_output("PT4_N2_supply_pressure",  val=200.0,  units="bar")
		sensors.add_output("TC4_run_dome_temp",       val=285.15, units="K")
		#endregion

		#region Subsystems

		# Run tank (PT2)
		self.add_subsystem(
			"RunTank",
			TankComponent(),
			promotes_inputs=[
				("m_fluid",     "run_tank_fluid_mass"),
				("rho_fluid",   "run_tank_density"),
				("p_tank_max",  "run_tank_pressure_PT2"),
				("diam_out",    "run_tank_diam"),
				("ullage_frac", "run_tank_ullage_frac"),
				("rho_wall",    "run_tank_wall_density"),
				("sigma_y",     "run_tank_yield_factor"),
			],
			promotes_outputs=[
				("v_internal",  "run_tank_volume"),
				("l_tank",      "run_tank_length"),
				("m_tank_dry",  "run_tank_dry_mass"),
			],
		)

		self.add_subsystem(
			"HybridEngine",
			HybridEngineGroup(cea=cea, rho_ox=rho_ox, rho_fuel=rho_fuel),
			promotes_inputs=[
				("engine_feed_pressure",   "run_tank_pressure_PT2"),
				("engine_prop_mass_init",  "test_prop_mass_init"),
				("engine_mixture_ratio",   "test_mixture_ratio"),
				("injector_area",          "injector_area"),
				("injector_cd",            "injector_cd"),
				("fuel_port_diam",         "fuel_port_diam"),
				("fuel_reg_exponent",      "fuel_reg_exponent"),
				("fuel_reg_ref",           "fuel_reg_ref"),
				("fuel_oxy_mass_flux_ref", "fuel_oxy_mass_flux_ref"),
				("nozzle_throat_area",     "nozzle_throat_area"),
				("nozzle_length",          "nozzle_length"),
				("nozzle_eta_friction",    "nozzle_eta_friction"),
			],
			promotes_outputs=[
				("engine_thrust",           "test_thrust"),
				("engine_chamber_pressure", "test_chamber_pressure_PT3"),
				("engine_chamber_temp",     "test_chamber_temp_TC3"),
				("engine_isp",              "test_isp"),
			],
		)
		#endregion

		#region Connections
		self.connect("Sensors.PT2_run_tank_pressure", "run_tank_pressure_PT2")
		#endregion
