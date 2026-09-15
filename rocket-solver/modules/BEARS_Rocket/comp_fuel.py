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

		self.add_output(
			"grain_diam", val=0.1, units="m",
			desc="Minimum necessary fuel grain diameter"
		)

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

		"""
		Normalized Marxman regression law:

		  r_dot = a (G_ox / G_0)^n

		where
		- `a` is the regression coefficient (at reference flux) [m/s]
		- `n` is the flux exponent [-],
		- `G_ox` is the oxidizer mass flux [kg/(m^2*s)], and
		- `G_0` is the reference mass flux (1.0 kg/(m^2*s))

		From here we have two options for calculating the outputs:
		- the ballistic sizing model (calculates fuel stack dimensions from
		  mixture ratio and mass flow), and
		- the geometric sizing model (calculates the mass flow and mixture
		  ratio resulting from given fuel stack dimensions)

		Here, we use the ballistic model:

		  mdot_fuel = mdot_ox / MR

		  length = mdot_fuel / (rho_fuel * pi * d_port * r_dot)

		From the other variables we calculate the minimum required fuel grain
		cylinder width:

		  d_grain = d_port + 2 * r_dot * t_burn

		TODO: In the current model, the entire burn chamber, including fuel
		      stack, is considered in 0D: thermodynamic variables and fuel
		      regression are assumed to be uniform. This is good enough for
		      preliminaries but should be refined down the line
		"""

		# Port area
		a_port = 0.25 * pi * d_port**2

		# Mass flux
		# We need this check to avoid Newton's method crashes
		if np.iscomplexobj(mdot_ox):
			# Directly eval analytic ops preserving imaginary part
			g_ox = mdot_ox / a_port
		else:
			# Caused by reversed flow (P_chamber > P_tank) in Newton's searches
			# Clamp to prevent NaN in fractional powers (g_ratio**n)
			g_ox = np.maximum(1e-6, mdot_ox) / a_port

		g_ratio = g_ox / g0

		# Regression rate
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
