#region Imports
import openmdao.api as om

from openmdao.api import Group, IndepVarComp

from ..BEARS_Chem import BEARS_Chem

from .comp_tank       import TankComponent
from .comp_split      import PropellantSplitComponent
from .comp_tank_oxy   import OxidizerTankComponent
from .comp_tank_press import PressurantTankComponent
from .group_engine    import HybridEngineGroup
#endregion

class TestStandGroup(Group):

	def initialize(self):
		self.options.declare("chem",                          types=BEARS_Chem)
		self.options.declare("rho_ox",         default=750.0, types=float)
		self.options.declare("rho_fuel",       default=900.0, types=float)
		self.options.declare("ox_wall_mat",    default=None)
		self.options.declare("press_wall_mat", default=None)

		self.options.declare(
			"tank_mode",
			default="facility",
			values=["facility", "flight"],
		)

	def setup(self):
		chem = self.options["chem"]

		mode = self.options["tank_mode"]

		ox_wall    = self.options["ox_wall_mat"]
		press_wall = self.options["press_wall_mat"]

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

		match mode:
			case "facility":

				self.set_input_defaults(
					"run_tank_pressure_PT2", val=60e5,        units="Pa"
				)

				self.set_input_defaults(
					"run_tank_density",      val=chem.rho_ox, units="kg/m**3"
				)

				self.set_input_defaults(
					"run_tank_fluid_mass",   val=10.0,        units="kg"
				)

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

				self.connect(
					"Sensors.PT2_run_tank_pressure",
					"run_tank_pressure_PT2"
				)

				feed_press_var = "run_tank_pressure_PT2"

			case "flight":

				self.set_input_defaults(
					"tank_pressure",  val=60e5,  units="Pa"
				)

				self.set_input_defaults(
					"press_pressure", val=200e5, units="Pa"
				)

				self.add_subsystem(
					"PropSplit",
					PropellantSplitComponent(),
					promotes_inputs=[
						("m_prop",        "test_prop_mass_init"),
						("mixture_ratio", "test_mixture_ratio"),
					],
				)

				self.add_subsystem(
					"OxidizerTank",
					OxidizerTankComponent(
						rho_ox=chem.rho_ox,
						wall_material=ox_wall,
					),
					promotes_inputs=[
						("p_tank_max",    "tank_pressure"),
						("diam_out",      "tank_diam"),
						("ullage_frac",   "tank_ullage_frac"),
						("sigma_y",       "tank_yield_factor"),
						("safety_factor", "tank_safety_factor"),
						("rho_wall",      "tank_wall_density"),
					],
					promotes_outputs=[
						("m_tank_dry",    "tank_dry_mass"),
						("l_tank",        "tank_length"),
						("v_internal",    "tank_volume"),
						("t_wall",        "tank_wall_thickness"),
						("t_liner",       "tank_liner_thickness"),
						("t_wrap",        "tank_wrap_thickness"),
					],
				)

				self.add_subsystem(
					"PressurantTank",
					PressurantTankComponent(wall_material=press_wall),
					promotes_inputs=[
						("p_tank_max",    "press_pressure"),
						("diam_out",      "press_diam"),
						("sigma_y",       "press_yield_factor"),
						("safety_factor", "press_safety_factor"),
						("rho_wall",      "press_wall_density"),
					],
					promotes_outputs=[
						("m_tank_dry",    "press_dry_mass"),
						("l_tank",        "press_length"),
						("v_internal",    "press_volume"),
						("t_wall",        "press_wall_thickness"),
						("m_press",       "press_press_mass"),
						("rho_press",     "press_press_density"),
					],
				)

				feed_press_var = "tank_pressure"

		self.add_subsystem(
			"HybridEngine",
			HybridEngineGroup(chem=chem),
			promotes_inputs=[
				("engine_feed_pressure",   feed_press_var),
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
