# region Imports
import numpy as np

from math       import pi
from .comp_tank import TankComponent
# endregion

class PressurantTankComponent(TankComponent):

	def initialize(self):
		super().initialize()
		self.options.declare("r_gas",    default=296.8,  types=float)
		self.options.declare("t_gas",    default=293.15, types=float)
		self.options.declare("z_factor", default=1.0,    types=float)

	def setup(self):
		super().setup()

		# Sizing inputs from the oxidizer system
		self.add_input("v_ox_displace", val=0.01, units="m**3")
		self.add_input("p_ox",          val=70e5, units="Pa")

		# Thermodynamic outputs
		self.add_output("m_press",      val=1.2,    units="kg")
		self.add_output("rho_press",    val=344.0,  units="kg/m**3")

	def get_fluid_density(self, inputs):
		p_max = inputs["p_tank_max"]
		r_gas = self.options["r_gas"]
		t_gas = self.options["t_gas"]
		z     = self.options["z_factor"]
		return p_max / (z * r_gas * t_gas)

	def get_fluid_mass(self, inputs):
		v_displace = inputs["v_ox_displace"]
		p_ox       = inputs["p_ox"]
		p_max      = inputs["p_tank_max"]

		r_gas = self.options["r_gas"]
		t_gas = self.options["t_gas"]
		z     = self.options["z_factor"]

		# Gas required to displace the oxidizer volume
		m_displace = (p_ox * v_displace) / (z * r_gas * t_gas)

		# Residual gas correction
		f_residual = p_ox / p_max
		m_press = m_displace / (1.0 - f_residual)

		return m_press

	def get_ullage_frac(self, inputs):
		return 0.0

	def compute(self, inputs, outputs):
		outputs["m_press"]   = self.get_fluid_mass(inputs)
		outputs["rho_press"] = self.get_fluid_density(inputs)

		super().compute(inputs, outputs)

