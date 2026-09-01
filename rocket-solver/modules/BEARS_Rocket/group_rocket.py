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
		self.options.declare("cea", types=CEA_Obj)
		self.options.declare("atm", types=BEARS_Atm)

	def setup(self):
		cea = self.options["cea"]
		atm = self.options["atm"]

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
		ivc.add_output("propellant_density",     val=1200.0, units="kg/m**3")
		ivc.add_output("nozzle_expansion_ratio", val=40.0)
		ivc.add_output("chamber_pressure",       val=35.0,   units="bar")
		ivc.add_output("structural_mass",        val=2.0,    units="kg")

		# OptimizationVars: specific parameters that we wish to optimize against
		ovc = self.add_subsystem("OptimizationVars", IndepVarComp())
		ovc.add_output("propellant_mass", val=10.0, units="kg")
		ovc.add_output("mixture_ratio",   val=1.0)
		#endregion

		#region Subsystems
		self.add_subsystem("Propulsion", PropulsionGroup(cea=cea))

		self.add_subsystem("Mass", MassComponent())

		self.add_subsystem(
			"Trajectory",
			TrajectoryComponent(atm=atm),
			promotes_outputs=["burn_time", "apogee"],
		)
		#endregion

		#region Connections
		# - Propulsion
		self.connect("DesignVars.tank_pressure",          "Propulsion.Tank.p_tank_max")
		self.connect("DesignVars.pressure_safety_factor", "Propulsion.Tank.safety_factor")
		self.connect("DesignVars.diameter",               "Propulsion.diam_out")
		self.connect("DesignVars.tank_ullage_fraction",   "Propulsion.Tank.ullage_frac")
		self.connect("DesignVars.tank_wall_yield_factor", "Propulsion.Tank.sigma_y")
		self.connect("DesignVars.tank_wall_density",      "Propulsion.Tank.rho_wall")
		self.connect("DesignVars.propellant_density",     "Propulsion.Tank.rho_ox")
		self.connect("DesignVars.nozzle_expansion_ratio", "Propulsion.expansion_ratio")
		self.connect("DesignVars.chamber_pressure",       "Propulsion.chamber_pressure")

		self.connect("OptimizationVars.propellant_mass",  "Propulsion.m_prop_i")

		# - Mass
		self.connect("DesignVars.payload_mass",           "Mass.payload_mass")
		self.connect("DesignVars.structural_mass",        "Mass.structural_mass")

		self.connect("OptimizationVars.propellant_mass",  "Mass.propellant_mass")
		self.connect("OptimizationVars.mixture_ratio",    "Propulsion.mixture_ratio")

		# - Trajectory
		self.connect("DesignVars.diameter", "Trajectory.diameter")

		self.connect("Propulsion.isp",      "Trajectory.isp")
		self.connect("Propulsion.thrust",   "Trajectory.thrust")
		self.connect("Mass.initial_mass",   "Trajectory.initial_mass")
		self.connect("Mass.dry_mass",       "Trajectory.dry_mass")
		#endregion
