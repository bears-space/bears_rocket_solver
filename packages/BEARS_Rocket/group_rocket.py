#region Imports
from openmdao.api import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_cea  import ChemComponent
from .comp_mass import MassComponent
from .comp_traj import TrajectoryComponent
#endregion

class RocketGroup(Group):

	def initialize(self):
		self.options.declare('cea', types=CEA_Obj)

	def setup(self):
		cea = self.options['cea']

		#region Subsystems
		self.add_subsystem(
			'Propulsion',
			ChemComponent(cea=cea),
			promotes_inputs=['mixture_ratio']
		)

		self.add_subsystem(
			'Mass',
			MassComponent(),
			promotes_inputs=['propellant_mass', 'payload_mass']
		)

		self.add_subsystem(
			'Trajectory',
			TrajectoryComponent(),
			promotes_outputs=['apogee']
		)
		#endregion

		#region Connections
		self.connect('Propulsion.isp', 'Trajectory.isp')
		self.connect('Propulsion.thrust', 'Trajectory.thrust')
		self.connect('Mass.initial_mass', 'Trajectory.initial_mass')
		self.connect('Mass.dry_mass', 'Trajectory.dry_mass')
		#endregion
