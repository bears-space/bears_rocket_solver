# region Imports
from openmdao.api      import ExplicitComponent
from rocketcea.cea_obj import CEA_Obj
# endregion

class ChemComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("cea", types=CEA_Obj)

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

		cea = self.options["cea"]

		pa_to_psia = 1.450377e-4 # 1 Pa = 1.45038e-4 psia
		fts_to_ms = 0.3048       # 1 ft/s = 0.3048 m/s

		pc_psia = chamber_pressure * pa_to_psia
		cstar   = cea.get_Cstar(Pc=pc_psia, MR=mixture_ratio) * fts_to_ms
		isp     = cea.get_Isp(Pc=pc_psia, MR=mixture_ratio, eps=expansion_ratio)
		tc_k    = cea.get_Tcomb(Pc=pc_psia, MR=mixture_ratio) * (5.0 / 9.0)

		outputs["cstar"]     = cstar
		outputs["isp"]       = isp
		outputs["t_chamber"] = tc_k
