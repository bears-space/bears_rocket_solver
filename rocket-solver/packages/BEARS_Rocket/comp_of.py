#region Imports
from openmdao.api      import ExplicitComponent
from rocketcea.cea_obj import CEA_Obj
#endregion

class OFComponent(ExplicitComponent):

	def __init__(self, cea: CEA_Obj, **kwargs):
		super().__init__(**kwargs)

		# Initialize the CEA object internally
		self.cea = cea

	def setup(self):
		# Input: Mixture ratio
		self.add_input('mixture_ratio', val=2.0)

		# Output: Characteristic velocity (m/s)
		self.add_output('cstar', val=1500.0)

	def setup_partials(self):
		# Declare partial derivatives
		# 'method=fd' tells OpenMDAO to use FiniteDifference
		self.declare_partials('cstar', 'mixture_ratio', method='fd')

	def compute(self, inputs, outputs):
		cstar = self.cea.get_Cstar(
			Pc  = 35.0, # Chamber pressure
			MR  = inputs['mixture_ratio'][0]
			#eps = 40.0, # Nozzle expansion area ratio
		)

		outputs['cstar'] = cstar
