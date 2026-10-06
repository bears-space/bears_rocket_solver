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
		self.add_input("m_oxy",         val=10.0,   units="kg")
		self.add_input("p_tank_max",    val=70e5,   units="Pa")
		self.add_input("diam_out",      val=0.15,   units="m")
		self.add_input("ullage_frac",   val=0.1)
		self.add_input("safety_factor", val=1.5)
		self.add_input("sigma_y",       val=276e6,  units="Pa")
		self.add_input("rho_wall",      val=2700.0, units="kg/m**3")

		self.add_output("t_wall",       val=0.002,  units="m")
		self.add_output("l_tank",       val=1.0,    units="m")
		self.add_output("v_internal",   val=0.012,  units="m**3")
		self.add_output("v_fluid",      val=0.010,  units="m**3")
		self.add_output("m_tank_dry",   val=2.0,    units="kg")
