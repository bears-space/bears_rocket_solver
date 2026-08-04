#region Imports
from openmdao.api import ExplicitComponent
#endregion

class MassComponent(ExplicitComponent):

	def setup(self):
		# Inputs
		self.add_input('payload_mass', val=2.0)

		self.add_input('propellant_mass', val=10.0)

		self.add_input('structural_coefficient', val=0.2)

		self.add_output('initial_mass', val=14.0)
		self.add_output('dry_mass', val=4.0)

	def setup_partials(self):
		self.declare_partials('*', '*', method='fd')

	def compute(self, inputs, outputs):
		m_prop    = inputs['propellant_mass']
		m_payload = inputs['payload_mass']
		k_struct  = inputs['structural_coefficient']

		m_dry = m_payload + (k_struct * m_prop)

		m_init = m_dry + m_prop

		outputs['dry_mass']     = m_dry
		outputs['initial_mass'] = m_init

