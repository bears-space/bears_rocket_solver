#region Imports
from openmdao.api import ExplicitComponent
#endregion

class PropellantSplitComponent(ExplicitComponent):
	"""Splits the propellant mass into oxidizer and fuel by mixture ratio"""

	def setup(self):
		# Burned propellant mass [kg]
		self.add_input("m_prop",        val=10.0, units="kg")
		# Oxidizer over fuel mass [-]
		self.add_input("mixture_ratio", val=6.0)

		self.add_output("m_ox",         val=8.57, units="kg")  # Ox mass
		self.add_output("m_fuel",       val=1.43, units="kg")  # Fuel mass

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		m_prop = inputs["m_prop"]
		mr     = inputs["mixture_ratio"]

		outputs["m_ox"]   = (m_prop * mr) / (mr + 1.0)
		outputs["m_fuel"] = m_prop / (mr + 1.0)
