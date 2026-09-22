# region Imports
from openmdao.api      import Group, IndepVarComp
from rocketcea.cea_obj import CEA_Obj

from ..BEARS_Atmo import BEARS_Atm

from .group_prop import PropulsionGroup
from .comp_mass  import MassComponent
from .comp_traj  import TrajectoryComponent
# endregion

class RocketGroup(Group):

	def initialize(self):
		self.options.declare("cea",      types=CEA_Obj)
		self.options.declare("atm",      types=BEARS_Atm)
		self.options.declare("rho_ox",   default=1200.0, types=float)
		self.options.declare("rho_fuel", default=900.0,  types=float)

	def setup(self):
		cea      = self.options["cea"]
		atm      = self.options["atm"]
		rho_ox   = self.options["rho_ox"]
		rho_fuel = self.options["rho_fuel"]

		#region Independent variable components
		# DesignVars:
		# catch-all for free design parameters
		ivc = self.add_subsystem("DesignVars", IndepVarComp())

		# - Global
		ivc.add_output("g_payload_mass",         val=1.0,    units="kg")
		ivc.add_output("g_target_altitude",      val=3000.0, units="m")
		ivc.add_output("g_diameter",             val=0.5,    units="m")

		# - Tank
		# NOTE: the tank component expects pressure in SI Pa units,
		#       here we specify the pressure in units of bar used by the team
		#       and let MDAO convert automatically on component boundary
		ivc.add_output("tank_pressure",          val=70,     units="bar")
		ivc.add_output("tank_safety_factor",     val=2.0)
		ivc.add_output("tank_ullage_fraction",   val=0.1)
		ivc.add_output("tank_wall_yield_factor", val=276e6,  units="Pa")
		ivc.add_output("tank_wall_density",      val=2700.0, units="kg/m**3")

		# - Injector
		ivc.add_output("injector_area",          val=4.5e-5, units="m**2")
		ivc.add_output("injector_cd",            val=0.7)

		# - Fuel
		ivc.add_output("fuel_port_diam",         val=0.05,   units="m")
		ivc.add_output("fuel_a_reg",             val=1.0e-4, units="m/s")
		ivc.add_output("fuel_n_reg",             val=0.5)
		ivc.add_output("fuel_oxy_mass_flux_ref", val=1.0, units="kg/(m**2*s)")

		# - Nozzle
		ivc.add_output("nozzle_throat_area",     val=5.0e-4, units="m**2")
		ivc.add_output("nozzle_expansion_ratio", val=40.0)
		ivc.add_output("nozzle_eta_friction",    val=0.95)
		ivc.add_output("nozzle_half_angle",      val=15.0, units="deg")

		# OptimizationVars:
		# specific parameters that we wish to optimize against
		ovc = self.add_subsystem("OptimizationVars", IndepVarComp())
		ovc.add_output("propellant_mass", val=10.0, units="kg")
		ovc.add_output("mixture_ratio",   val=6.0)
		#endregion

		#region Subsystems
		self.add_subsystem(
			"Propulsion",
			PropulsionGroup(cea=cea, rho_ox=rho_ox, rho_fuel=rho_fuel),
		)

		self.add_subsystem("Mass", MassComponent())

		self.add_subsystem(
			"Trajectory",
			TrajectoryComponent(atm=atm),
			promotes_outputs=["burn_time", "apogee"],
		)
		#endregion

		#region Connections
		# - Tank
		self.connect("DesignVars.tank_pressure",          "Propulsion.p_tank")
		self.connect("DesignVars.tank_safety_factor",     "Propulsion.Tank.safety_factor")
		self.connect("DesignVars.g_diameter",             "Propulsion.diam_out")
		self.connect("DesignVars.tank_ullage_fraction",   "Propulsion.Tank.ullage_frac")
		self.connect("DesignVars.tank_wall_yield_factor", "Propulsion.Tank.sigma_y")
		self.connect("DesignVars.tank_wall_density",      "Propulsion.Tank.rho_wall")

		# - Fuel
		self.connect("DesignVars.fuel_port_diam",         "Propulsion.port_diam")
		self.connect("DesignVars.fuel_a_reg",             "Propulsion.a_reg")
		self.connect("DesignVars.fuel_n_reg",             "Propulsion.n_reg")
		self.connect("DesignVars.fuel_oxy_mass_flux_ref", "Propulsion.Fuel.g0_ref")

		self.connect("OptimizationVars.mixture_ratio",   "Propulsion.mixture_ratio")

		# - Injector
		self.connect("DesignVars.injector_area",          "Propulsion.a_inj")
		self.connect("DesignVars.injector_cd",            "Propulsion.cd")

		# - Nozzle
		self.connect("DesignVars.nozzle_expansion_ratio", "Propulsion.expansion_ratio")
		self.connect("DesignVars.nozzle_throat_area",     "Propulsion.a_throat")
		self.connect("DesignVars.nozzle_eta_friction",    "Propulsion.Nozzle.eta_friction")
		self.connect("DesignVars.nozzle_half_angle",      "Propulsion.Nozzle.half_angle")

		# - Mass
		self.connect("DesignVars.g_payload_mass",         "Mass.payload_mass")

		self.connect("Propulsion.m_tank_dry",             "Mass.structural_mass")

		self.connect("OptimizationVars.propellant_mass",  "Propulsion.m_prop_i")
		self.connect("OptimizationVars.propellant_mass",  "Mass.propellant_mass")

		# - Trajectory
		self.connect("DesignVars.g_diameter", "Trajectory.diameter")

		self.connect("Propulsion.isp",      "Trajectory.isp")
		self.connect("Propulsion.thrust",   "Trajectory.thrust")
		self.connect("Mass.initial_mass",   "Trajectory.initial_mass")
		self.connect("Mass.dry_mass",       "Trajectory.dry_mass")
		#endregion
