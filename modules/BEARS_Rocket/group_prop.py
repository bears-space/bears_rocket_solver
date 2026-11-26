#region Imports
from openmdao.api import Group

from ..BEARS_Chem   import BEARS_Chem
from ..BEARS_Thermo import PressurantThermoModel
from ..Config       import Gas, Wall

from .comp_split      import PropellantSplitComponent
from .comp_tank_oxy   import OxidizerTankComponent
from .comp_tank_press import PressurantTankComponent
from .group_engine    import HybridEngineGroup
#endregion

class PropulsionGroup(Group):
	"""Propulsion system: split, ox tank, pressurant bottle, engine"""

	def initialize(self):
		# Chemistry of the propellant combination
		self.options.declare("chem",         types=BEARS_Chem)
		# Oxidizer tank wall layup
		self.options.declare("ox_wall",      types=Wall)
		# Pressurant bottle wall layup
		self.options.declare("press_wall",   types=Wall)
		# Pressurant gas
		self.options.declare("press_gas",    types=Gas)
		# Pressurant blowdown model
		self.options.declare("press_thermo", types=PressurantThermoModel)

	def setup(self):
		chem = self.options["chem"]

		#region Subsystems
		self.add_subsystem(
			"PropSplit",
			PropellantSplitComponent(),
			promotes_inputs=[
				("m_prop",        "prop_prop_mass_init"),
				("mixture_ratio", "prop_mixture_ratio"),
			],
		)

		# The oxidizer tank comes before the pressurant bottle, which sizes
		# itself to the oxidizer volume
		self.add_subsystem(
			"OxidizerTank",
			OxidizerTankComponent(
				rho_ox = chem.rho_ox,
				wall   = self.options["ox_wall"],
			),
			promotes_inputs=[
				("p_tank_max",    "tank_pressure"),
				("diam_out",      "tank_diam"),
				("ullage_frac",   "tank_ullage_frac"),
				("safety_factor", "tank_safety_factor"),
				("boss_len_fwd",  "tank_boss_len_fwd"),
				("boss_len_aft",  "tank_boss_len_aft"),
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
			PressurantTankComponent(
				wall         = self.options["press_wall"],
				gas          = self.options["press_gas"],
				thermo_model = self.options["press_thermo"],
			),
			promotes_inputs=[
				("p_tank_max",    "press_pressure"),
				("diam_out",      "press_diam"),
				("safety_factor", "press_safety_factor"),
				("boss_len_fwd",  "press_boss_len_fwd"),
				("boss_len_aft",  "press_boss_len_aft"),
				("p_reg_margin",  "press_reg_margin"),
				("t_ambient",     "press_ambient_temp"),
				("p_sat",         "tank_vapor_pressure"),
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
			HybridEngineGroup(chem=chem),
			promotes_inputs=[
				("engine_feed_pressure",      "tank_pressure"),
				("engine_prop_mass_init",     "prop_prop_mass_init"),
				("engine_mixture_ratio",      "prop_mixture_ratio"),
				("injector_area",             "injector_area"),
				("injector_cd",               "injector_cd"),
				("fuel_port_diam",            "fuel_port_diam"),
				("fuel_reg_exponent",         "fuel_reg_exponent"),
				("fuel_reg_ref",              "fuel_reg_ref"),
				("fuel_oxy_mass_flux_ref",    "fuel_oxy_mass_flux_ref"),
				("nozzle_exit_diam",          "nozzle_exit_diam"),
				("nozzle_throat_area",        "nozzle_throat_area"),
				("conical_nozzle_half_angle", "conical_nozzle_half_angle"),
				("nozzle_eta_friction",       "nozzle_eta_friction"),
				("fuel_eta_reg",              "fuel_eta_reg"),
				("chem_eta_cstar",            "chem_eta_cstar"),
			],
			promotes_outputs=[
				("engine_thrust",           "prop_thrust"),
				("engine_chamber_pressure", "prop_chamber_pressure"),
				("engine_chamber_temp",     "prop_chamber_temp"),
				("engine_isp",              "prop_isp"),
				("nozzle_exit_area",        "nozzle_exit_area"),
				("nozzle_expansion_ratio",  "nozzle_expansion_ratio"),
				("nozzle_exit_mach",        "nozzle_exit_mach"),
				("nozzle_length",           "nozzle_length"),
				("injector_delta_p",        "injector_delta_p"),
				("fuel_length",             "fuel_length"),
				("fuel_grain_diam",         "fuel_grain_diam"),
				("fuel_regression_rate",    "fuel_regression_rate"),
			],
		)
		#endregion

		#region Connections
		self.connect("PropSplit.m_ox",       "OxidizerTank.m_oxy")
		self.connect("OxidizerTank.v_fluid", "PressurantTank.v_ox_displace")
		self.connect("tank_pressure",        "PressurantTank.p_ox")
		self.connect("tank_ullage_frac",     "PressurantTank.ox_ullage_frac")
		#endregion
