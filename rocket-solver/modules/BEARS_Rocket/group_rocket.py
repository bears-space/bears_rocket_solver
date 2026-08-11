# region Imports
from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from ..BEARS_Atmo import BEARS_Atm

from .comp_cea  import ChemComponent
from .comp_mass import MassComponent
from .comp_traj import TrajectoryComponent
# endregion

class RocketGroup(Group):

	def initialize(self):
		self.options.declare("cea", types=CEA_Obj)
		self.options.declare("atm", types=BEARS_Atm)

	def setup(self):
		cea = self.options["cea"]
		atm = self.options["atm"]

		# region Subsystems
		self.add_subsystem(
			"Propulsion",
			ChemComponent(cea=cea),
			promotes_inputs=["mixture_ratio"],
		)

		self.add_subsystem(
			"Mass",
			MassComponent(),
			promotes_inputs=["propellant_mass", "payload_mass"],
		)

		self.add_subsystem(
			"Trajectory",
			TrajectoryComponent(atm=atm),
			promotes_inputs=["diameter"],
			promotes_outputs=["burn_time", "apogee"],
		)
		# endregion

		# region Connections
		self.connect("Propulsion.isp",    "Trajectory.isp")
		self.connect("Propulsion.thrust", "Trajectory.thrust")
		self.connect("Mass.initial_mass", "Trajectory.initial_mass")
		self.connect("Mass.dry_mass",     "Trajectory.dry_mass")
		# endregion
