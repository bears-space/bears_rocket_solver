"""
@author: Andrii
@date:   03.08.2026
"""

#region Imports
from openmdao.api import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_of   import OFComponent
from .comp_mass import MassComponent
#endregion

class RocketGroup(Group):

	def initialize(self):
		self.options.declare('cea', types=CEA_Obj)

	def setup(self):
		cea = self.options['cea']

		self.add_subsystem(
			'prop',
			OFComponent(cea=cea),
			promotes_inputs=['mixture_ratio']
		)

		self.add_subsystem(
			'mass',
			MassComponent(),
			promotes_inputs=['propellant_mass', 'payload_mass']
		)
