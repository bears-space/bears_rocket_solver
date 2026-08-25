#region Imports
from openmdao.api import ExplicitComponent
#endregion

class NozzleComponent(ExplicitComponent):

	def setup(self):
		self.add_input('p_tank', val=50e5, units='Pa')
