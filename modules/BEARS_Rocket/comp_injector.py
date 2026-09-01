#region Imports
import numpy as np

from openmdao.api import ExplicitComponent
#endregion

class InjectorComponent(ExplicitComponent):

	def initialize(self):
		# Liquid oxidizer density
		self.options.declare("rho_ox", default=1200.0, types=float)

	def setup(self):
		self.add_input("p_tank",    val=30e5,   units="Pa")
		self.add_input("p_chamber", val=20e5,   units="Pa")
		self.add_input("a_inj",     val=4.5e-5, units="m**2")

		# Discharge coefficient (efficiency) TODO
		self.add_input("cd", val=0.7)

		self.add_output("mdot_ox", val=1.0, units="kg/s")

	def setup_partials(self):
		self.declare_partials("mdot_ox", "*", method="cs")

	def compute(self, inputs, outputs):
		p_up   = inputs["p_tank"]
		p_down = inputs["p_chamber"]
		area   = inputs["a_inj"]
		cd     = inputs["cd"]

		rho = self.options["rho_ox"]

		# Upstream (tank) to downstream (fuel chamber) pressure difference
		delta_p = p_up - p_down

		# Account for possible negative pressure difference (reverse flow)
		if delta_p >= 0:
			mdot =  cd * area * np.sqrt(2.0 * rho * delta_p)
		else:
			mdot = -cd * area * np.sqrt(2.0 * rho * (-delta_p))

		outputs["mdot_ox"] = mdot
