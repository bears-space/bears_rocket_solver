# region Imports
from openmdao.api import ExplicitComponent

from ..BEARS_Chem import Thermochemistry
# endregion

class ChemComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("chem", types=Thermochemistry)

	def setup(self):
		self.add_input("chamber_pressure", val=35e5, units="Pa")
		self.add_input("mixture_ratio",    val=6.0)
		self.add_input("expansion_ratio",  val=40.0) # Expansion area ratio

		self.add_output("cstar",     val=1500.0, units="m/s") # Characteristic velocity
		self.add_output("isp",       val=120.0,  units="s")
		self.add_output("t_chamber", val=3000.0, units="K")

	def setup_partials(self):
		self.declare_partials(
			["isp", "cstar", "t_chamber"],
			["chamber_pressure", "mixture_ratio"],
			method="fd",
			step=1e-4,
		)

	def compute(self, inputs, outputs):
		chamber_pressure = inputs["chamber_pressure"][0]
		mixture_ratio    = inputs["mixture_ratio"][0]
		expansion_ratio  = inputs["expansion_ratio"][0]

		chem = self.options["chem"]

		outputs["cstar"]     = chem.get_cstar(chamber_pressure, mixture_ratio)
		outputs["t_chamber"] = chem.get_tcomb(chamber_pressure, mixture_ratio)
		outputs["isp"]       = chem.get_isp(
			chamber_pressure,
			mixture_ratio,
			expansion_ratio,
		)
