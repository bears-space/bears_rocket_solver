#region Imports
from math         import pi
import numpy      as np
from openmdao.api import ExplicitComponent
#endregion

class FuelComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("rho_fuel", default=900.0, types=float)

	def setup(self):
		self.add_input("mdot_ox",        val=1.0,  units="kg/s")
		self.add_input("m_prop_i",       val=10.0, units="kg")
		self.add_input("port_diam",      val=0.05, units="m")
		self.add_input("mixture_ratio",  val=6.0)

		# Regression coefficients
		self.add_input(
			"a_reg", val=1.0e-4, units="m/s",
			desc="Fuel regression rate at reference mass flux"
		)

		self.add_input("n_reg", val=0.5, desc="Mass flux exponent")

		self.add_input(
			"g0_ref", val=1.0, units="kg/(m**2*s)",
			desc="Reference oxidizer mass flux"
		)

		self.add_output("r_dot",      val=0.002, units="m/s")
		self.add_output("length",     val=0.4,   units="m")
		self.add_output("grain_diam", val=0.1,   units="m")
		self.add_output("m_fuel",     val=1.5,   units="kg")
		self.add_output("mdot_fuel",  val=0.15,  units="kg/s")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		m_prop  = inputs["m_prop_i"]
		d_port  = inputs["port_diam"]
		mr      = inputs["mixture_ratio"]

		a  = inputs["a_reg"]
		n  = inputs["n_reg"]
		g0 = inputs["g0_ref"]

		rho_fuel = self.options["rho_fuel"]

		# Port area and mass flux
		a_port = 0.25 * pi * d_port**2
		if np.iscomplexobj(mdot_ox):
			g_ox = mdot_ox / a_port
		else:
			g_ox = np.maximum(1e-6, mdot_ox) / a_port
		g_ratio = g_ox / g0

		# Regression rate: r_dot = a * (G_ox / G_0)^n
		r_dot = a * (g_ratio**n)

		# Fuel flow and dependent stack length
		mdot_fuel = mdot_ox / mr
		a_burn    = mdot_fuel / (rho_fuel * r_dot)
		length    = a_burn / (pi * d_port)

		# Fuel mass and web burn
		m_fuel = m_prop / (mr + 1.0)
		t_burn = m_prop / (mdot_ox + mdot_fuel)
		w_burn = r_dot * t_burn

		outputs["r_dot"]      = r_dot
		outputs["length"]     = length
		outputs["grain_diam"] = d_port + 2.0 * w_burn
		outputs["m_fuel"]     = m_fuel
		outputs["mdot_fuel"]  = mdot_fuel
