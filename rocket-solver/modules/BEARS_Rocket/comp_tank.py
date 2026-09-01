# region Imports
from math import pi

from openmdao.api import ExplicitComponent
# endregion

class TankComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("rho_ox", default=1200.0, types=float)

	def setup(self):
		self.add_input("m_prop_i",      val=10.0,   units="kg")
		self.add_input("mixture_ratio", val=6.0)

		self.add_input("p_tank_max",    val=60e5,   units="Pa")
		self.add_input("diam_out",      val=0.5,    units="m")
		self.add_input("ullage_frac",   val=0.1)

		self.add_input("safety_factor", val=1.5)
		self.add_input("sigma_y",       val=276e6,  units="Pa")
		self.add_input("rho_wall",      val=2700.0, units="kg/m**3")

		self.add_output("t_wall",       val=0.002,  units="m")
		self.add_output("l_tank",       val=5.0,    units="m")
		self.add_output("v_internal",   val=5.0,    units="m**3")
		self.add_output("m_tank_dry",   val=2.0,    units="kg")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		m_prop  = inputs["m_prop_i"]
		f_prop  = inputs["mixture_ratio"]
		rho_ox  = self.options["rho_ox"]
		p_max   = inputs["p_tank_max"]
		d_out   = inputs["diam_out"]
		uf      = inputs["ullage_frac"]
		sigma_y = inputs["sigma_y"]
		sf      = inputs["safety_factor"]
		rho_w   = inputs["rho_wall"]

		# Extract oxidizer mass from the propellant mass and mixture ratio
		m_ox = (m_prop * f_prop) / (f_prop + 1)

		# Hoop stress
		# https://www.engineersedge.com/material_science/hoop-stress.htm
		sigma_safe = sigma_y / sf
		r_out = d_out / 2.0
		t_wall = (p_max * r_out) / (sigma_safe + p_max)

		r_in = r_out - t_wall
		d_in = 2.0 * r_in

		# Volumes and lengths
		v_prop = m_ox / rho_ox
		v_int = v_prop / (1.0 - uf)
		v_caps = (4.0 / 3.0) * pi * r_in**3 # Hemispherical caps
		v_cyl = max(0.0, v_int - v_caps)
		a_int = pi * r_in**2
		l_cyl = v_cyl / a_int
		l_tot = l_cyl + d_out
		v_ext = (pi * r_out**2 * l_cyl) + ((4.0 / 3.0) * pi * r_out**3)
		v_struct = v_ext - v_int

		m_dry = v_struct * rho_w

		outputs["t_wall"]     = t_wall
		outputs["l_tank"]     = l_tot
		outputs["v_internal"] = v_int
		outputs["m_tank_dry"] = m_dry
