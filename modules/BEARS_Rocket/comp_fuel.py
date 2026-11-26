#region Imports
from math         import pi
import numpy      as np
from openmdao.api import ExplicitComponent
#endregion

class FuelComponent(ExplicitComponent):
	"""
	Hybrid fuel grain with a single circular port, sized ballistically

	The regression rate follows the normalized Marxman law

	  r_dot = eta_reg * a * (G_ox / G_ref)^n

	with the oxidizer mass flux G_ox = mdot_ox / A_port. The fuel mass flow
	follows from the mixture ratio, and the port length from the burning
	surface it needs:

	  mdot_fuel = mdot_ox / MR
	  length    = mdot_fuel / (rho_fuel * pi * d_port * r_dot)

	The grain outer diameter is the port grown by the web burned over burn:

	  d_grain = d_port + 2 * r_dot * t_burn

	TODO: the chamber is modeled in 0D, so the regression is uniform along
	      the port and does not change as the port grows. Good enough for
	      preliminary sizing, to be refined
	"""

	def initialize(self):
		# Fuel grain density [kg/m^3]
		self.options.declare("rho_fuel", types=float)

	def setup(self):
		# Oxidizer mass flow [kg/s]
		self.add_input("mdot_ox",       val=1.0,    units="kg/s")
		# Burned propellant mass [kg]
		self.add_input("m_prop_i",      val=10.0,   units="kg")
		# Port diameter [m]
		self.add_input("port_diam",     val=0.05,   units="m")
		# Oxidizer over fuel mass flow [-]
		self.add_input("mixture_ratio", val=6.0)
		# Regression law exponent n [-]
		self.add_input("n_reg",         val=0.5)
		# Regression rate a at the reference flux [m/s]
		self.add_input("reg_ref",       val=1.0e-4, units="m/s")
		# Reference oxidizer mass flux G_ref [kg/(m^2*s)]
		self.add_input("g_ox_ref",      val=1.0,    units="kg/(m**2*s)")
		# Real over modeled regression rate [-]
		self.add_input("eta_reg",       val=1.0)

		# Regression rate [m/s]
		self.add_output("r_dot",      val=0.002, units="m/s")
		# Grain length [m]
		self.add_output("length",     val=0.4,   units="m")
		# Grain outer diameter, the port at burnout [m]
		self.add_output("grain_diam", val=0.1,   units="m")
		# Fuel mass flow [kg/s]
		self.add_output("mdot_fuel",  val=0.15,  units="kg/s")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		d_port  = inputs["port_diam"]
		mr      = inputs["mixture_ratio"]

		a_port = 0.25 * pi * d_port**2

		# Newton iterations can reverse the oxidizer flow. The flux is held
		# positive so the fractional power stays real, except under complex
		# step, where the derivative has to pass through
		if np.iscomplexobj(mdot_ox):
			g_ox = mdot_ox / a_port
		else:
			g_ox = np.maximum(1e-6, mdot_ox) / a_port

		flux_ratio = g_ox / inputs["g_ox_ref"]
		r_dot      = (
			inputs["eta_reg"] * inputs["reg_ref"]
			* flux_ratio ** inputs["n_reg"]
		)

		mdot_fuel = mdot_ox / mr
		length    = mdot_fuel / (
			self.options["rho_fuel"] * r_dot * pi * d_port
		)
		t_burn    = inputs["m_prop_i"] / (mdot_ox + mdot_fuel)

		outputs["r_dot"]      = r_dot
		outputs["length"]     = length
		outputs["grain_diam"] = d_port + 2.0 * r_dot * t_burn
		outputs["mdot_fuel"]  = mdot_fuel
