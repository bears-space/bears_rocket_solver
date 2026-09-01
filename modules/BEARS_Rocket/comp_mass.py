# region Imports
from typing import override
from openmdao.api import ExplicitComponent
# endregion

class MassComponent(ExplicitComponent):

	def setup(self):
		# Inputs
		self.add_input("payload_mass",    val=2.0,  units="kg")
		self.add_input("propellant_mass", val=10.0, units="kg")
		self.add_input("structural_mass", val=2.0,  units="kg")

		self.add_output("initial_mass", val=14.0, units="kg")
		self.add_output("dry_mass",     val=4.0,  units="kg")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		m_prop    = inputs["propellant_mass"]
		m_payload = inputs["payload_mass"]
		m_struct  = inputs["structural_mass"]

		m_dry = m_payload + m_struct
		m_init = m_dry + m_prop

		outputs["dry_mass"]     = m_dry
		outputs["initial_mass"] = m_init
