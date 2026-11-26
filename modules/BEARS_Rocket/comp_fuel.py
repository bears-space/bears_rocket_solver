#region Imports
from math         import pi
import numpy      as np
from openmdao.api import ExplicitComponent
#endregion

class FuelComponent(ExplicitComponent):
	"""
	Hybrid fuel grain with a single circular port, sized ballistically

	The instantaneous regression rate follows the normalized Marxman law

	  r_dot = eta_reg * a * (G_ox / G_ref)^n

	with the oxidizer mass flux

	  G_ox = mdot_ox / A_port = mdot_ox / (pi * r^2)

	At constant oxidizer mass flow, separating

	  dr/dt = r_dot_0 * (r_0 / r)^(2n)

	over [0, t_burn] with N = 2n + 1 gives the burnout radius

	  r_f        = (r_0^N + N * r_o^(2n) * r_dot_0 * t_burn)^(1 / N)
	  grain_diam = 2 * r_f

	Grain length follows from the exact annular fuel volume burned over [0,
	t_burn], ensuring mass conservation for every component n > 0:

	  length = m_fuel / (rho_fuel * pi * (r_f^2 - r_0^2))

	with rho = r_f / r_0, the exact ignition and burnout mixture ratios around
	the burn-averaged mixture ratio MR are:

	  MR_0 = MR * (N / 2) * (rho^2 - 1) / (rho^N - 1)
	  MR_f = MR_0 * rho^(2n - 1)

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

		# Initial regression rate at port_diam [m/s]
		self.add_output("r_dot",               val=0.002, units="m/s")
		# Grain length [m]
		self.add_output("length",              val=0.4,   units="m")
		# Grain outer diameter, the port at burnout [m]
		self.add_output("grain_diam",          val=0.1,   units="m")
		# Burn-averaged fuel mass flow [kg/s]
		self.add_output("mdot_fuel",           val=0.15,  units="kg/s")
		# Ignition mixture ratio [-]
		self.add_output("mixture_ratio_init",  val=6.0)
		# Burnout mixture ratio [-]
		self.add_output("mixture_ratio_final", val=6.0)

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		r_0     = 0.5 * inputs["port_diam"]
		mr      = inputs["mixture_ratio"]
		n       = inputs["n_reg"]
		eta     = inputs["eta_reg"]
		a_ref   = inputs["reg_ref"]
		g_ref   = inputs["g_ox_ref"]
		m_0     = inputs["m_prop_i"]

		rho_fuel = self.options["rho_fuel"]

		a_port = pi * r_0**2

		# Newton iterations can reverse the oxidizer flow. The flux is held
		# positive so the fractional power stays real, except under complex
		# step, where the derivative has to pass through
		if np.iscomplexobj(mdot_ox):
			mdot_ox_pos = mdot_ox
		else:
			mdot_ox_pos = np.maximum(1e-6, mdot_ox)

		g_ox       = mdot_ox_pos / a_port
		flux_ratio = g_ox / g_ref
		r_dot_0    = eta * a_ref * flux_ratio**n

		mdot_fuel = mdot_ox / mr
		m_fuel    = m_0 / (mr + 1.0)
		t_burn    = (m_0 * mr) / ((mr + 1.0) * mdot_ox_pos)

		# Integrate dr/dt = r_dot_0 * (r_0 / r)^(2n) over [0, t_burn]
		n_exp = 2.0 * n + 1.0
		r_f   = (
			r_0**n_exp + n_exp * r_0**(2.0 * n) * r_dot_0 * t_burn
		)**(1.0 / n_exp)

		# Size grain length from the exact annular volume burned
		area_burned = pi * (r_f**2 - r_0**2)
		length      = m_fuel / (rho_fuel * area_burned)

		# Ignition and burnout mixture ratios and burn-averaged MR
		rad_ratio = r_f / r_0
		mr_init   = (
			mr * 0.5 * n_exp
			* (rad_ratio**2 - 1.0) / (rad_ratio**n_exp - 1.0)
		)
		mr_final  = mr_init * rad_ratio**(2.0 * n - 1.0)

		outputs["r_dot"]               = r_dot_0
		outputs["length"]              = length
		outputs["grain_diam"]          = 2.0 * r_f
		outputs["mdot_fuel"]           = mdot_fuel
		outputs["mixture_ratio_init"]  = mr_init
		outputs["mixture_ratio_final"] = mr_final
