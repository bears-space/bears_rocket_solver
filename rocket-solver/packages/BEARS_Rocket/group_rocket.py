"""
@author: Andrii
@date:   03.08.2026
"""

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

		self.add_subsystem(
			'prop',
			ChemComponent(cea=cea)
			#promotes_inputs=['mixture_ratio']
		)

		self.add_subsystem(
			'mass',
			MassComponent(),
			promotes_inputs=['propellant_mass', 'payload_mass']
		)

		self.add_subsystem(
			'traj',
			TrajectoryComponent(),
			promotes_outputs=['apogee']
		)

		self.connect('prop.isp', 'traj.isp')
		self.connect('prop.thrust', 'traj.thrust')
		self.connect('mass.initial_mass', 'traj.initial_mass')
		self.connect('mass.dry_mass', 'traj.dry_mass')
