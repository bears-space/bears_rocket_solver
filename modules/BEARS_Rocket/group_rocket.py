#region Imports
from openmdao.api import Group, IndepVarComp, ExecComp

from ..BEARS_Atmo   import BEARS_Atm
from ..BEARS_Chem   import BEARS_Chem
from ..BEARS_Thermo import PressurantThermoModel
from ..Config       import RocketConfig, Gas, Wall

from .group_prop import PropulsionGroup
from .comp_mass  import MassComponent
from .comp_traj  import TrajectoryComponent
#endregion

class RocketGroup(Group):
	"""
	The whole rocket: propulsion, mass budget and trajectory

	The independent variables are taken from the rocket inputs, with the
	units of the input file. OpenMDAO converts them to SI at each connection
	"""

	def initialize(self):
		# Rocket design inputs
		self.options.declare("cfg",          types=RocketConfig)
		# Chemistry of the propellant combination
		self.options.declare("chem",         types=BEARS_Chem)
		# Atmosphere model
		self.options.declare("atm",          types=BEARS_Atm)
		# Oxidizer tank wall layup
		self.options.declare("ox_wall",      types=Wall)
		# Pressurant bottle wall layup
		self.options.declare("press_wall",   types=Wall)
		# Pressurant gas
		self.options.declare("press_gas",    types=Gas)
		# Pressurant blowdown model
		self.options.declare("press_thermo", types=PressurantThermoModel)

	def setup(self):
		cfg  = self.options["cfg"]
		chem = self.options["chem"]
		gl   = cfg.cfg_global
		ox   = cfg.cfg_oxy_tank
		pr   = cfg.cfg_press_tank
		fu   = cfg.cfg_fuel
		nz   = cfg.cfg_nozzle
		ef   = cfg.cfg_efficiencies
		op   = cfg.cfg_optim

		#region Independent variables
		# DesignVars: fixed design parameters
		ivc = self.add_subsystem("DesignVars", IndepVarComp())

		# - Vehicle
		# Everything except the propulsion system [kg]
		ivc.add_output(
			"g_non_propulsion_mass",
			val=gl.non_propulsion_mass_kg,
			units="kg",
		)
		# Engine hardware without propellant [kg]
		ivc.add_output(
			"g_engine_dry_mass",
			val=gl.engine_dry_mass_kg,
			units="kg",
		)
		# Apogee target [m]
		ivc.add_output(
			"g_target_altitude",
			val=gl.target_altitude_m,
			units="m",
		)
		# Thrust target [N]
		ivc.add_output(
			"g_target_thrust",
			val=gl.target_thrust_N,
			units="N",
		)
		# Chamber pressure target [bar]
		ivc.add_output(
			"g_target_chamber_pressure",
			val=gl.target_chamber_pressure_bar,
			units="bar",
		)

		# The tanks are structural and form the skin, so they take the outer
		# diameter, which also sets the drag. The engine is not structural
		# and sits inside the bore, the inner diameter
		# Airframe bore [m]
		ivc.add_output(
			"g_inner_diameter",
			val=gl.inner_rocket_diameter_m,
			units="m",
		)
		# Airframe skin [m]
		ivc.add_output(
			"g_outer_diameter",
			val=gl.outer_rocket_diameter_m,
			units="m",
		)
		# Outer diameter the non-propulsion mass is given at [m]
		ivc.add_output(
			"g_ref_outer_diameter",
			val=gl.outer_rocket_diameter_m,
			units="m",
		)

		# - Oxidizer tank
		# Maximum operating pressure [bar]
		ivc.add_output("tank_pressure",        val=ox.pressure_bar, units="bar")
		# Burst over operating pressure [-]
		ivc.add_output("tank_safety_factor",   val=ox.safety_factor)
		# Gas-filled share at loading [-]
		ivc.add_output("tank_ullage_fraction", val=ox.ullage_fraction)
		# Forward boss length [m]
		ivc.add_output(
			"tank_boss_len_fwd", val=ox.boss_length_fwd_m, units="m",
		)
		# Aft boss length [m]
		ivc.add_output(
			"tank_boss_len_aft", val=ox.boss_length_aft_m, units="m",
		)
		# Oxidizer saturation pressure [Pa]
		ivc.add_output("tank_vapor_pressure",  val=chem.p_vap_ox, units="Pa")

		# - Pressurant bottle
		# Fill pressure [bar]
		ivc.add_output("press_pressure",      val=pr.pressure_bar, units="bar")
		# Burst over fill pressure [-]
		ivc.add_output("press_safety_factor", val=pr.safety_factor)
		# Forward boss length [m]
		ivc.add_output(
			"press_boss_len_fwd", val=pr.boss_length_fwd_m, units="m",
		)
		# Aft boss length [m]
		ivc.add_output(
			"press_boss_len_aft", val=pr.boss_length_aft_m, units="m",
		)
		# Bottle pressure left over the tank pressure at burnout [bar]
		ivc.add_output(
			"press_reg_margin", val=pr.reg_margin_bar, units="bar",
		)
		# Bottle temperature at fill [degC]
		ivc.add_output(
			"press_ambient_temp", val=pr.ambient_temp_c, units="degC",
		)

		# - Engine
		# Injector discharge coefficient [-]
		ivc.add_output("injector_cd",       val=cfg.cfg_injector.cd)
		# Initial port diameter [m]
		ivc.add_output("fuel_port_diam",    val=fu.port_diam_m, units="m")
		# Regression law exponent [-]
		ivc.add_output("fuel_reg_exponent", val=fu.reg_exponent)
		# Regression rate at the reference flux [m/s]
		ivc.add_output("fuel_reg_ref",      val=fu.reg_ref_ms, units="m/s")
		# Reference oxidizer mass flux [kg/(m^2*s)]
		ivc.add_output(
			"fuel_oxy_mass_flux_ref",
			val=fu.oxy_mass_flux_ref_kgm2s,
			units="kg/(m**2*s)",
		)
		# Nozzle exit diameter [m]
		ivc.add_output(
			"nozzle_exit_diam", val=nz.nozzle_exit_diameter_m, units="m",
		)
		# Divergent cone half angle [deg]
		ivc.add_output(
			"conical_nozzle_half_angle",
			val=nz.conical_nozzle_half_angle_deg,
			units="deg",
		)

		# EfficiencyVars: efficiencies on the ideal models [-]
		evc = self.add_subsystem("EfficiencyVars", IndepVarComp())
		# Delivered over ideal c* [-]
		evc.add_output("eta_combustion",      val=ef.combustion)
		# Real over 1D apogee [-]
		evc.add_output("eta_trajectory",      val=ef.trajectory)
		# Burned over loaded propellant [-]
		evc.add_output("eta_propellant",      val=ef.propellant_utilization)
		# Real over modeled regression rate [-]
		evc.add_output("eta_regression",      val=ef.regression_correction)
		# Thrust left after wall friction [-]
		evc.add_output("eta_nozzle_friction", val=ef.nozzle_friction)

		# OptimizationVars: design variables at optimizer start values
		ovc = self.add_subsystem("OptimizationVars", IndepVarComp())
		# Burned propellant mass [kg]
		ovc.add_output(
			"o_propellant_mass",
			val=op.propellant_mass_kg.start,
			units="kg",
		)
		# Oxidizer over fuel mass flow [-]
		ovc.add_output("o_mixture_ratio", val=op.mixture_ratio.start)
		# Total injector orifice area [m^2]
		ovc.add_output(
			"o_injector_area",
			val=op.injector_area_m2.start,
			units="m**2",
		)
		# Nozzle throat area [m^2]
		ovc.add_output(
			"o_nozzle_throat_area",
			val=op.nozzle_throat_area_m2.start,
			units="m**2",
		)
		#endregion

		#region Subsystems
		self.add_subsystem(
			"Propulsion",
			PropulsionGroup(
				chem         = chem,
				ox_wall      = self.options["ox_wall"],
				press_wall   = self.options["press_wall"],
				press_gas    = self.options["press_gas"],
				press_thermo = self.options["press_thermo"],
			),
		)

		self.add_subsystem("Mass", MassComponent())

		# Radial room between the fuel grain and the airframe bore
		self.add_subsystem(
			"EngineFit",
			ExecComp(
				"grain_margin = d_inner - d_grain",
				# Bore diameter left over the grain [m]
				grain_margin = {"units": "m"},
				d_inner      = {"units": "m"},  # Airframe bore
				d_grain      = {"units": "m"},  # Fuel grain outer diameter
			),
		)

		self.add_subsystem(
			"Trajectory",
			TrajectoryComponent(atm=self.options["atm"], aero=cfg.cfg_aero),
			promotes_outputs=["burn_time", "apogee"],
		)
		#endregion

		#region Connections
		connections = (
			# - Oxidizer tank
			("DesignVars.tank_pressure",     "Propulsion.tank_pressure"),
			("DesignVars.g_outer_diameter",  "Propulsion.tank_diam"),
			(
				"DesignVars.tank_safety_factor",
				"Propulsion.tank_safety_factor",
			),
			("DesignVars.tank_ullage_fraction", "Propulsion.tank_ullage_frac"),
			("DesignVars.tank_boss_len_fwd", "Propulsion.tank_boss_len_fwd"),
			("DesignVars.tank_boss_len_aft", "Propulsion.tank_boss_len_aft"),
			(
				"DesignVars.tank_vapor_pressure",
				"Propulsion.tank_vapor_pressure",
			),
			# - Pressurant bottle
			("DesignVars.press_pressure",    "Propulsion.press_pressure"),
			("DesignVars.g_outer_diameter",  "Propulsion.press_diam"),
			(
				"DesignVars.press_safety_factor",
				"Propulsion.press_safety_factor",
			),
			("DesignVars.press_boss_len_fwd", "Propulsion.press_boss_len_fwd"),
			("DesignVars.press_boss_len_aft", "Propulsion.press_boss_len_aft"),
			("DesignVars.press_reg_margin",   "Propulsion.press_reg_margin"),
			("DesignVars.press_ambient_temp", "Propulsion.press_ambient_temp"),
			# - Fuel
			("DesignVars.fuel_port_diam",    "Propulsion.fuel_port_diam"),
			("DesignVars.fuel_reg_exponent", "Propulsion.fuel_reg_exponent"),
			("DesignVars.fuel_reg_ref",      "Propulsion.fuel_reg_ref"),
			(
				"DesignVars.fuel_oxy_mass_flux_ref",
				"Propulsion.fuel_oxy_mass_flux_ref",
			),
			# - Injector
			("DesignVars.injector_cd",       "Propulsion.injector_cd"),
			# - Nozzle
			("DesignVars.nozzle_exit_diam",  "Propulsion.nozzle_exit_diam"),
			(
				"DesignVars.conical_nozzle_half_angle",
				"Propulsion.conical_nozzle_half_angle",
			),
			# - Engine fit
			("DesignVars.g_inner_diameter",  "EngineFit.d_inner"),
			("Propulsion.fuel_grain_diam",   "EngineFit.d_grain"),
			# - Mass
			("DesignVars.g_non_propulsion_mass", "Mass.non_propulsion_mass"),
			("DesignVars.g_engine_dry_mass",     "Mass.engine_dry_mass"),
			("DesignVars.g_outer_diameter",      "Mass.diameter"),
			("DesignVars.g_ref_outer_diameter",  "Mass.ref_diameter"),
			("Propulsion.tank_dry_mass",         "Mass.ox_tank_mass"),
			("Propulsion.press_dry_mass",        "Mass.press_tank_mass"),
			("Propulsion.press_press_mass",      "Mass.pressurant_mass"),
			# - Trajectory
			("DesignVars.g_outer_diameter",  "Trajectory.diameter"),
			("Propulsion.prop_isp",          "Trajectory.isp"),
			("Propulsion.prop_thrust",       "Trajectory.thrust"),
			("Mass.initial_mass",            "Trajectory.initial_mass"),
			# - Efficiencies
			("EfficiencyVars.eta_regression",  "Propulsion.fuel_eta_reg"),
			("EfficiencyVars.eta_combustion",  "Propulsion.chem_eta_cstar"),
			("EfficiencyVars.eta_propellant",  "Mass.eta_prop"),
			(
				"EfficiencyVars.eta_nozzle_friction",
				"Propulsion.nozzle_eta_friction",
			),
			# - Optimization
			(
				"OptimizationVars.o_propellant_mass",
				"Trajectory.propellant_mass",
			),
			(
				"OptimizationVars.o_mixture_ratio",
				"Propulsion.prop_mixture_ratio",
			),
			(
				"OptimizationVars.o_propellant_mass",
				"Propulsion.prop_prop_mass_init",
			),
			("OptimizationVars.o_propellant_mass", "Mass.propellant_mass"),
			("OptimizationVars.o_injector_area",   "Propulsion.injector_area"),
			(
				"OptimizationVars.o_nozzle_throat_area",
				"Propulsion.nozzle_throat_area",
			),
		)
		for src, dst in connections:
			self.connect(src, dst)
		#endregion
