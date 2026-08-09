# region Imports
from openmdao.api import ExplicitComponent

from ..BEARS_Atmo import BEARS_Atm
# endregion

class AtmoComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("atm", types=BEARS_Atm)

	def setup(self):
		self.add_input("altitude", val=0.0, units="m")

		self.add_output("pressure",       val=101325.0, units="Pa")
		self.add_output("temperature",    val=228.15,   units="K")
		self.add_output("density",        val=1.225,    units="kg/m**3")
		self.add_output("speed_of_sound", val=340.29,   units="m/s")

	def setup_partials(self):
		self.declare_partials("*", "altitude", method="fd")

	def compute(self, inputs, outputs):
		h = inputs["altitude"][0]

		atm = self.options["atm"]

		T, P, rho, a = atm(h)

		outputs["temperature"]    = T
		outputs["pressure"]       = P
		outputs["density"]        = rho
		outputs["speed_of_sound"] = a
