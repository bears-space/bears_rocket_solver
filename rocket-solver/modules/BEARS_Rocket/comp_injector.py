#region Imports
import numpy as np

from openmdao.api import ExplicitComponent
#endregion

class InjectorComponent(ExplicitComponent):

	def setup(self):
		self.add_input('p_tank', val=50e5, units='Pa')
		self.add_input('p_chamber', val=35e5, units='Pa')
		self.add_input('rho_ox', val=1200.0, units='kg/m**3')
		self.add_input('a_inj', val=1e-4, units='m**2')
		self.add_input('cd', val=0.7) # Discharge coefficient (efficiency)

		self.add_output('mdot_ox', val=1.0, units='kg/s')

	def setup_partials(self):
		self.declare_partials('mdot_ox', '*', method='fd')

	def compute(self, inputs, outputs):
		p_up   = inputs['p_tank']
		p_down = inputs['p_chamber']
		rho    = inputs['rho_liq']
		area   = inputs['a_inj']
		cd     = inputs['cd']

		delta_p = p_up - p_down

		if delta_p > 0:
			outputs['mdot_ox'] = cd * area * np.sqrt(2 * rho * delta_p)
		else:
			# Prevent backflow calculation or imaginary numbers in sqrt
			outputs['mdot_ox'] = 0.0
