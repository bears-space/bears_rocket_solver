#region Imports
from .comp_tank import TankComponent
#endregion

class OxidizerTankComponent(TankComponent):
	"""Tank of liquid oxidizer, with a gas-filled ullage on top"""

	def initialize(self):
		super().initialize()
		# Liquid oxidizer density [kg/m^3]
		self.options.declare("rho_ox", types=float)

	def setup(self):
		super().setup()
		# Oxidizer mass to store [kg]
		self.add_input("m_oxy",       val=10.0, units="kg")
		# Gas-filled share of the tank volume at loading [-]
		self.add_input("ullage_frac", val=0.1)

	def compute(self, inputs, outputs):
		self.size_tank(
			inputs,
			outputs,
			inputs["m_oxy"][0],
			self.options["rho_ox"],
			inputs["ullage_frac"][0],
		)
