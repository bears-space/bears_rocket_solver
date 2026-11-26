#region Imports
import numpy as np

from math         import pi
from openmdao.api import ExplicitComponent

from ..Config       import CONSTANTS
from ..BEARS_Thermo import IsentropicState
#endregion

g = CONSTANTS.universal.standard_gravity  # Standard gravity [m/s^2]

# The nozzle is choked, so the flow at the throat is exactly sonic
MACH_THROAT = 1.0

class NozzleGeometryComponent(ExplicitComponent):
	"""
	Conical converging-diverging nozzle geometry

	The exit diameter is fixed and the throat area is free, so the expansion
	ratio follows from the two, eps = A_e / A_t

	The divergent section is a cone of half angle theta, whose radius grows
	linearly from r_t to r_e, so its length is L = (r_e - r_t) / tan(theta)
	"""

	def setup(self):
		# Exit diameter [m]
		self.add_input("d_exit",     val=0.065,  units="m")
		# Throat area [m^2]
		self.add_input("a_throat",   val=7.0e-4, units="m**2")
		# Half angle of the divergent cone [rad]
		self.add_input("half_angle", val=0.26,   units="rad")

		# Exit area [m^2]
		self.add_output("a_exit",          val=3.3e-3, units="m**2")
		# Exit over throat area [-]
		self.add_output("expansion_ratio", val=4.7)
		# Divergent section length, throat to exit [m]
		self.add_output("length",          val=0.05,   units="m")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		d_e   = inputs["d_exit"]
		a_t   = inputs["a_throat"]
		theta = inputs["half_angle"]

		a_e = 0.25 * pi * d_e**2
		r_e = 0.5 * d_e
		r_t = np.sqrt(a_t / pi)

		outputs["a_exit"]          = a_e
		outputs["expansion_ratio"] = a_e / a_t
		outputs["length"]          = (r_e - r_t) / np.tan(theta)

class NozzleComponent(ExplicitComponent):
	"""
	Choked flow through a conical converging-diverging nozzle

	The throat is sonic (M = 1), so the isentropic choked-flow relation fixes
	the chamber pressure for a given mass flow through the throat area:

	  mdot = A_t * p_c / sqrt(R * T_c) * MFP(M = 1, gamma)

	defining characteristic velocity c* = sqrt(R * T_c) / MFP(1, gamma)

	The delivered Isp is the ideal one less the divergence loss of the cone,
	lambda = (1 + cos(theta)) / 2, and the wall friction loss
	"""

	def setup(self):
		# Oxidizer mass flow [kg/s]
		self.add_input("mdot_ox",         val=1.0,    units="kg/s")
		# Oxidizer over fuel mass flow [-]
		self.add_input("mixture_ratio",   val=6.0)
		# Chamber temperature [K]
		self.add_input("t_chamber",       val=3000.0, units="K")
		# Ratio of specific heats of the chamber gas [-]
		self.add_input("gamma",           val=1.2)
		# Molar mass of the chamber gas [kg/mol]
		self.add_input("molar_mass",      val=0.025,  units="kg/mol")
		# Sea-level Isp before nozzle losses [s]
		self.add_input("isp",             val=300.0,  units="s")
		# Combustion efficiency on c* [-]
		self.add_input("eta_cstar",       val=1.0)
		# Throat area [m^2]
		self.add_input("a_throat",        val=7.0e-4, units="m**2")
		# Exit over throat area [-]
		self.add_input("expansion_ratio", val=4.7)
		# Half angle of the divergent cone [rad]
		self.add_input("half_angle",      val=0.26,   units="rad")
		# Thrust left after wall friction [-]
		self.add_input("eta_friction",    val=0.95)

		# Exit Mach number [-]
		self.add_output("mach_exit",     val=3.0)
		# Characteristic velocity, combustion losses included [m/s]
		self.add_output("cstar",         val=1500.0, units="m/s")
		# Chamber pressure [Pa]
		self.add_output("p_chamber",     val=30e5,   units="Pa")
		# Static pressure at the throat [Pa]
		self.add_output("p_throat",      val=17e5,   units="Pa")
		# Static temperature at the throat [K]
		self.add_output("t_throat",      val=2700.0, units="K")
		# Static pressure at the exit [Pa]
		self.add_output("p_exit",        val=1e5,    units="Pa")
		# Propellant mass flow, oxidizer and fuel [kg/s]
		self.add_output("mdot_prop",     val=1.5,    units="kg/s")
		# Delivered thrust [N]
		self.add_output("thrust",        val=3000.0, units="N")
		# Delivered sea-level Isp [s]
		self.add_output("isp_delivered", val=200.0,  units="s")
		# Divergence times friction efficiency [-]
		self.add_output("eta_nozzle",    val=0.96)

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mr    = inputs["mixture_ratio"]
		t_c   = inputs["t_chamber"]
		gamma = inputs["gamma"][0]
		a_t   = inputs["a_throat"]

		# Conical divergence loss and wall friction
		div_loss      = 0.5 * (1.0 + np.cos(inputs["half_angle"]))
		eta_nozzle    = div_loss * inputs["eta_friction"]
		isp_delivered = inputs["isp"] * eta_nozzle

		# Choked flow at the sonic throat sets the chamber pressure
		throat    = IsentropicState.from_mach(MACH_THROAT, gamma)
		r_uni     = CONSTANTS.universal.molar_gas_constant
		r_gas     = r_uni / inputs["molar_mass"]
		cstar     = inputs["eta_cstar"] * np.sqrt(r_gas * t_c) / throat.mfp
		mdot_prop = inputs["mdot_ox"] * (mr + 1.0) / mr
		p_c       = mdot_prop * cstar / a_t

		# Isentropic expansion to supersonic exit, A_e/A_t = eps
		eps       = inputs["expansion_ratio"][0]
		exit_flow = IsentropicState.from_eps_sup(eps, gamma)

		outputs["mach_exit"]     = exit_flow.mach
		outputs["cstar"]         = cstar
		outputs["p_chamber"]     = p_c
		outputs["p_throat"]      = p_c * throat.p_ratio
		outputs["t_throat"]      = t_c * throat.t_ratio
		outputs["p_exit"]        = p_c * exit_flow.p_ratio
		outputs["mdot_prop"]     = mdot_prop
		# F = mdot * Isp * g0
		outputs["thrust"]        = mdot_prop * isp_delivered * g
		outputs["isp_delivered"] = isp_delivered
		outputs["eta_nozzle"]    = eta_nozzle
