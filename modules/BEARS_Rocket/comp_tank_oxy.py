# region Imports
import numpy as np

from math       import pi
from .comp_tank import TankComponent
# endregion

class OxidizerTankComponent(TankComponent):

	def initialize(self):
		super().initialize()
		self.options.declare("rho_ox", default=700.0, types=float)

	def get_fluid_mass(self, inputs):
		return inputs["m_oxy"]

	def get_fluid_density(self, inputs):
		return self.options["rho_ox"]

	def setup(self):
		super().setup()
		self.add_input("m_oxy", val=10.0, units="kg")
