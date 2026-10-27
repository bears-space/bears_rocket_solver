#region Imports
import numpy as np

from scipy.constants import pi, g
from openmdao.api    import ExplicitComponent
#endregion

class NozzleComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare(
			"contour_type",
			default="conical",
			values=["ideal", "conical", "rao", "custom"],
		)

	def setup(self):
		# Thermodynamics
		self.add_input("mdot_ox",          val=1.0,    units="kg/s")
		self.add_input("mixture_ratio",    val=6.0)
		self.add_input("cstar",            val=1500.0, units="m/s")
		self.add_input("isp",              val=300.0,  units="s")

		# Geometry
		self.add_input("a_throat",         val=5e-4,   units="m**2")
		self.add_input("expansion_ratio",  val=40.0)
		self.add_input("length",           val=0.20,   units="m")

		# Viscous friction efficiency
		self.add_input("eta_friction",     val=0.95)

		self.add_output("p_chamber",       val=20e5,   units="Pa")
		self.add_output("mdot_prop",       val=1.16,   units="kg/s")
		self.add_output("thrust",          val=3000.0, units="N")
		self.add_output("eta_nozzle",      val=0.96)
		self.add_output("exit_half_angle", val=15.0,   units="deg")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		mr      = inputs["mixture_ratio"]
		cstar   = inputs["cstar"]
		isp     = inputs["isp"]
		a_t     = inputs["a_throat"]
		eps     = inputs["expansion_ratio"]
		length  = inputs["length"]
		eta_fr  = inputs["eta_friction"]

		contour = self.options["contour_type"]

		DEG2RAD = pi / 180.0
		RAD2DEG = 180.0 / pi

		r_t = np.sqrt(a_t / pi)
		r_e = r_t * np.sqrt(eps)

		# Divergence factor
		match contour:
			case "ideal":
				lam, theta_e = 1.0, 0.0
			case "conical":
				lam, theta_e = self._compute_conical(r_t, r_e, length)
			case "rao":
				lam, theta_e = self._compute_rao(r_t, r_e, length)
			case "custom":
				lam, theta_e = self._compute_custom(r_t, r_e, length)
			case _:
				lam, theta_e = self._compute_conical(r_t, r_e, length)

		eta_nozzle = lam * eta_fr

		# Choked flow mass and chamber pressure
		mdot_prop = mdot_ox * (mr + 1.0) / mr
		p_c       = (mdot_prop * cstar) / a_t

		# Isp = v_e / g = F / (mdot * g)  =>  F = mdot * Isp * g
		# Modulate with nozzle efficiency
		thrust = mdot_prop * isp * g * eta_nozzle

		outputs["mdot_prop"]       = mdot_prop
		outputs["p_chamber"]       = p_c
		outputs["thrust"]          = thrust
		outputs["eta_nozzle"]      = eta_nozzle
		outputs["exit_half_angle"] = theta_e * RAD2DEG

	#region Contour handlers
	def _compute_conical(self, r_t, r_e, length):
		# Straight cone: tan(alpha) = (r_e - r_t) / length
		alpha = np.arctan((r_e - r_t) / length)
		lam   = 0.5 * (1.0 + np.cos(alpha))
		return lam, alpha

	def _compute_rao(self, r_t, r_e, length):
		alpha_cone = np.arctan((r_e - r_t) / length)
		theta_e    = 0.4 * alpha_cone
		lam        = 0.5 * (1.0 + np.cos(theta_e))
		return lam, theta_e

	def _compute_custom(self, r_t, r_e, length):
		# TODO: Custom nozzle shapes, discrete radius arrays r(z)
		return self._compute_conical(r_t, r_e, length)
	#endregion

