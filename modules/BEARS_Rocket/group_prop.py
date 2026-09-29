# region Imports
import openmdao.api as om

from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_split      import PropellantSplitComponent
from .comp_tank_oxy   import OxidizerTankComponent
from .comp_tank_press import PressurantTankComponent
from .group_engine    import HybridEngineGroup
# endregion

class PropulsionGroup(Group):

	def initialize(self):
		self.options.declare("cea",      types=CEA_Obj)
		self.options.declare("rho_ox",   default=700.0, types=float)
		self.options.declare("rho_fuel", default=900.0, types=float)

	def setup(self):
		cea      = self.options["cea"]
		rho_ox   = self.options["rho_ox"]
		rho_fuel = self.options["rho_fuel"]

		self.set_input_defaults("tank_pressure", val=70e5, units="Pa")

		#region Subsystems
		self.add_subsystem(
			"PropSplit",
			PropellantSplitComponent(),
			promotes_inputs=[
				("m_prop",        "prop_prop_mass_init"),
				("mixture_ratio", "prop_mixture_ratio"),
			],
		)

		# NOTE: we put the oxidizer tank component here first before the
		#       pressurant tank component for it to evaluate before its
		#       `v_fluid` for the pressurant component to use
		self.add_subsystem(
			"OxidizerTank",
			OxidizerTankComponent(rho_ox=rho_ox),
			promotes_inputs=[
				("p_tank_max",    "tank_pressure"),
				("diam_out",      "tank_diam"),
				("ullage_frac",   "tank_ullage_frac"),
				("sigma_y",       "tank_yield_factor"),
				("safety_factor", "tank_safety_factor"),
				("rho_wall",      "tank_wall_density"),
			],
			promotes_outputs=[
				("m_tank_dry", "tank_dry_mass"),
				("l_tank",     "tank_length"),
				("v_internal", "tank_volume"),
				("t_wall",     "tank_wall_thickness"),
			],
		)

		self.add_subsystem(
			"PressurantTank",
			PressurantTankComponent(),
			promotes_inputs=[
				("p_tank_max",    "press_pressure"),
				("diam_out",      "press_diam"),
				("sigma_y",       "press_yield_factor"),
				("safety_factor", "press_safety_factor"),
				("rho_wall",      "press_wall_density"),
			],
			promotes_outputs=[
				("m_tank_dry", "press_dry_mass"),
				("l_tank",     "press_length"),
				("v_internal", "press_volume"),
				("t_wall",     "press_wall_thickness"),
				("m_press",    "press_press_mass"),
				("rho_press",  "press_press_density"),
			],
		)

		self.add_subsystem(
			"HybridEngine",
			HybridEngineGroup(cea=cea, rho_ox=rho_ox, rho_fuel=rho_fuel),
			promotes_inputs=[
				("engine_feed_pressure",   "tank_pressure"),
				("engine_prop_mass_init",  "prop_prop_mass_init"),
				("engine_mixture_ratio",   "prop_mixture_ratio"),
				("injector_area",          "injector_area"),
				("injector_cd",            "injector_cd"),
				("fuel_port_diam",         "fuel_port_diam"),
				("fuel_reg_exponent",      "fuel_reg_exponent"),
				("fuel_reg_ref",           "fuel_reg_ref"),
				("fuel_oxy_mass_flux_ref", "fuel_oxy_mass_flux_ref"),
				("nozzle_throat_area",     "nozzle_throat_area"),
				("nozzle_expansion_ratio", "nozzle_expansion_ratio"),
				("nozzle_length",          "nozzle_length"),
				("nozzle_eta_friction",    "nozzle_eta_friction"),
			],
			promotes_outputs=[
				("engine_thrust",           "prop_thrust"),
				("engine_chamber_pressure", "prop_chamber_pressure"),
				("engine_isp",              "prop_isp"),
				("injector_delta_p",        "injector_delta_p"),
				("fuel_length",             "fuel_length"),
				("fuel_grain_diam",         "fuel_grain_diam"),
				("fuel_regression_rate",    "fuel_regression_rate"),
				("fuel_mass",               "fuel_mass"),
			],
		)
		#endregion

		#region Connections
		self.connect("PropSplit.m_ox",        "OxidizerTank.m_oxy")
		self.connect("OxidizerTank.v_fluid",  "PressurantTank.v_ox_displace")
		self.connect("tank_pressure",         "PressurantTank.p_ox")
		#endregion

