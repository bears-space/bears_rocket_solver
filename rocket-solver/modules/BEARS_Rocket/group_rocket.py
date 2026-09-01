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
		cea    = self.options["cea"]
		atm    = self.options["atm"]
		rho_ox = self.options["rho_ox"]

		#region Independent variable components
		# DesignVars: catch-all for free design parameters
		ivc = self.add_subsystem("DesignVars", IndepVarComp())
		ivc.add_output("payload_mass",           val=1.0,    units="kg")
		ivc.add_output("target_altitude",        val=3000.0, units="m")
		ivc.add_output("diameter",               val=0.5,    units="m")
		ivc.add_output("tank_pressure",          val=50e5,   units="Pa")
		ivc.add_output("pressure_safety_factor", val=2.0)

		ivc.add_output("tank_ullage_fraction",   val=0.1)
		ivc.add_output("tank_wall_yield_factor", val=276e6,  units="Pa")
		ivc.add_output("tank_wall_density",      val=2700.0, units="kg/m**3")
		ivc.add_output("nozzle_expansion_ratio", val=40.0)
		ivc.add_output("structural_mass",        val=2.0,    units="kg")

		ivc.add_output("injector_area",          val=4.5e-5, units="m**2")
		ivc.add_output("injector_cd",            val=0.7)
		ivc.add_output("throat_area",            val=5.0e-4, units="m**2")

		# OptimizationVars: specific parameters that we wish to optimize against
		ovc = self.add_subsystem("OptimizationVars", IndepVarComp())
		ovc.add_output("propellant_mass", val=10.0, units="kg")
		ovc.add_output("mixture_ratio",   val=1.0)
		#endregion

		#region Subsystems
		self.add_subsystem(
			"Propulsion",
			PropulsionGroup(cea=cea, rho_ox=rho_ox),
		)

		self.add_subsystem("Mass", MassComponent())

		self.add_subsystem(
			"Trajectory",
			TrajectoryComponent(atm=atm),
			promotes_outputs=["burn_time", "apogee"],
		)
		#endregion

		#region Connections
		# - Propulsion
		self.connect("DesignVars.tank_pressure",          "Propulsion.p_tank")
		self.connect("DesignVars.pressure_safety_factor", "Propulsion.Tank.safety_factor")
		self.connect("DesignVars.diameter",               "Propulsion.diam_out")
		self.connect("DesignVars.tank_ullage_fraction",   "Propulsion.Tank.ullage_frac")
		self.connect("DesignVars.tank_wall_yield_factor", "Propulsion.Tank.sigma_y")
		self.connect("DesignVars.tank_wall_density",      "Propulsion.Tank.rho_wall")
		self.connect("DesignVars.nozzle_expansion_ratio", "Propulsion.expansion_ratio")
		self.connect("DesignVars.injector_area",          "Propulsion.a_inj")
		self.connect("DesignVars.injector_cd",            "Propulsion.cd")
		self.connect("DesignVars.throat_area",            "Propulsion.a_throat")

		self.connect("OptimizationVars.propellant_mass",  "Propulsion.m_prop_i")

		# - Mass
		self.connect("DesignVars.payload_mass",           "Mass.payload_mass")

		self.connect("Propulsion.m_tank_dry",             "Mass.structural_mass")

		self.connect("OptimizationVars.propellant_mass",  "Mass.propellant_mass")
		self.connect("OptimizationVars.mixture_ratio",    "Propulsion.mixture_ratio")

		# - Trajectory
		self.connect("DesignVars.diameter", "Trajectory.diameter")

		self.connect("Propulsion.isp",      "Trajectory.isp")
		self.connect("Propulsion.thrust",   "Trajectory.thrust")
		self.connect("Mass.initial_mass",   "Trajectory.initial_mass")
		self.connect("Mass.dry_mass",       "Trajectory.dry_mass")
		#endregion
