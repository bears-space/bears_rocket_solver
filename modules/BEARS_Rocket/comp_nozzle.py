#region Imports
import numpy as np

from scipy.constants import g
from openmdao.api    import ExplicitComponent
#endregion

class NozzleComponent(ExplicitComponent):

	def setup(self):
		self.add_input("mdot_ox",       val=1.0,    units="kg/s")
		self.add_input("mixture_ratio", val=6.0)
		self.add_input("cstar",         val=1500.0, units="m/s")
		self.add_input("isp",           val=300.0,  units="s")
		self.add_input("a_throat",      val=5e-4,   units="m**2")

		self.add_input("eta_friction",  val=0.95) # Viscous friction efficiency

		self.add_output("p_chamber",    val=20e5,   units="Pa")
		self.add_output("mdot_prop",    val=1.16,   units="kg/s")
		self.add_output("thrust",       val=3000.0, units="N")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		mdot_ox = inputs["mdot_ox"]
		mr      = inputs["mixture_ratio"]
		cstar   = inputs["cstar"]
		isp     = inputs["isp"]
		a_t     = inputs["a_throat"]
		eta     = inputs["eta_friction"]

		# Modulate the characteristic velocity
		# with empirical nozzle efficiency
		cstar_actual = eta * cstar

		# Mass flow of the exhaust mixture
		mdot_prop = mdot_ox * (mr + 1.0) / mr

		# Choked flow equation
		p_c = (mdot_prop * cstar_actual) / a_t

		#    Isp = v_e / g = F / (mdot * g)
		# => F = mdot * Isp * g
		thrust = mdot_prop * isp * g

		outputs["mdot_prop"] = mdot_prop
		outputs["p_chamber"] = p_c
		outputs["thrust"]    = thrust
