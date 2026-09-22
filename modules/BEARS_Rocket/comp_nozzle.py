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
		self.add_input("mdot_ox",       val=1.0,    units="kg/s")
		self.add_input("mixture_ratio", val=6.0)
		self.add_input("cstar",         val=1500.0, units="m/s")
		self.add_input("isp",           val=300.0,  units="s")
		self.add_input("a_throat",      val=5e-4,   units="m**2")
		self.add_input("half_angle",    val=15.0, units="deg")

		# Viscous friction efficiency
		self.add_input("eta_friction",  val=0.95)

		self.add_output("p_chamber",    val=20e5,   units="Pa")
		self.add_output("mdot_prop",    val=1.16,   units="kg/s")
		self.add_output("thrust",       val=3000.0, units="N")
		self.add_output("eta_nozzle",   val=0.96)

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		mr      = inputs["mixture_ratio"]
		cstar   = inputs["cstar"]
		isp     = inputs["isp"]
		a_t     = inputs["a_throat"]
		lam_ha  = inputs["half_angle"]
		eta_fr  = inputs["eta_friction"]

		contour = self.options["contour_type"]

		# Divergence factor
		match contour:
			case "ideal":
				lam = 1.0
			case "conical":
				alpha = lam_ha * pi / 180 # Degrees to radians
				lam = 0.5 * (1.0 + np.cos(alpha))
			case "rao":
				# TODO proper calc for Rao bell
				lam = 0.992
			# TODO custom nozzle shapes

		eta_nozzle = lam * eta_fr

		# Mass flow of the exhaust mixture
		mdot_prop = mdot_ox * (mr + 1.0) / mr

		# Choked flow equation
		p_c = (mdot_prop * cstar) / a_t

		# Isp = v_e / g = F / (mdot * g)  =>  F = mdot * Isp * g
		# Modulate with nozzle efficiency
		thrust = mdot_prop * isp * g * eta_nozzle

		outputs["mdot_prop"]  = mdot_prop
		outputs["p_chamber"]  = p_c
		outputs["thrust"]     = thrust
		outputs["eta_nozzle"] = eta_nozzle
