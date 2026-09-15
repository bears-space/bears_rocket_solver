#region Imports
from math         import pi
from openmdao.api import ExplicitComponent
#endregion

class FuelComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("rho_fuel", default=900.0, types=float)

	def setup(self):
		self.add_input("mdot_ox",    val=1.0,  units="kg/s")
		self.add_input("m_prop_i",   val=10.0, units="kg")
		self.add_input("port_diam",  val=0.05, units="m")
		self.add_input("grain_diam", val=0.10, units="m")

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

		self.add_output("r_dot",         val=0.002, units="m/s")
		self.add_output("length",        val=0.4,   units="m")
		self.add_output("m_fuel",        val=1.5,   units="kg")
		self.add_output("mdot_fuel",     val=0.15,  units="kg/s")
		self.add_output("mixture_ratio", val=6.0)

	def setup_partials(self):
		self.declare_partials(
			["length", "m_fuel", "mdot_fuel", "mixture_ratio"],
			["mdot_ox", "m_prop_i", "port_diam", "grain_diam", "a_reg", "n_reg"],
			method="cs",
		)

		self.declare_partials(
			"r_dot",
			["mdot_ox", "port_diam", "a_reg", "n_reg", "g0_ref"],
			method="cs",
		)

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		m_prop  = inputs["m_prop_i"]
		d_port  = inputs["port_diam"]
		d_grain = inputs["grain_diam"]

		a  = inputs["a_reg"]
		n  = inputs["n_reg"]
		g0 = inputs["g0_ref"]

		rho_fuel = self.options["rho_fuel"]

		# Port area and mass flux
		a_port  = 0.25 * pi * d_port**2
		g_ox    = mdot_ox / a_port
		g_ratio = g_ox / g0

		# Regression rate: r_dot = a * (G_ox / G_0)^n
		r_dot = a * (g_ratio**n)

		# Grain cross-section
		a_cross = 0.25 * pi * (d_grain**2 - d_port**2)

		#
		#   m_fuel = m_prop / (MR + 1)
		#   L = m_fuel / (rho_fuel * A_cross)
		#   mdot_fuel = rho_fuel * (pi * d_port * L) * r_dot
		#   MR = mdot_ox / mdot_fuel
		#
		# Geometric sizing:
		#
		#   MR = (mdot_ox * A_cross) / (pi * d_port * m_prop * r_dot - mdot_ox * A_cross)
		#
		# Alternatively, ballistic sizing:
		#
		#   beta = (4 * d_port * r_dot * m_prop) / (mdot_ox * (d_grain^2 - d_port^2))
		#

		term = (pi * d_port * r_dot * m_prop) / (a_cross * mdot_ox)
		mr = 1.0 / max(1e-4, term - 1.0)

		m_fuel = m_prop / (mr + 1.0)
		length = m_fuel / (rho_fuel * a_cross)

		a_burn    = pi * d_port * length
		mdot_fuel = rho_fuel * a_burn * r_dot

		outputs["r_dot"]         = r_dot
		outputs["mdot_fuel"]     = mdot_fuel
		outputs["mixture_ratio"] = mdot_ox / mdot_fuel
