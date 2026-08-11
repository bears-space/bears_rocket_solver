# region Imports
from openmdao.api      import ExplicitComponent
from rocketcea.cea_obj import CEA_Obj
# endregion

class ChemComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("cea", types=CEA_Obj)

	def setup(self):
		self.add_input("chamber_pressure", val=35.0, units="bar")
		self.add_input("mixture_ratio",    val=6.0)
		self.add_input("expansion_ratio",  val=40.0) # expansion area ratio

		self.add_output("cstar",  val=1500.0, units="m/s") # characteristic velocity
		self.add_output("isp",    val=120.0,  units="s")
		self.add_output("thrust", val=120.0,  units="N")

	def setup_partials(self):
		# Declare partial derivatives
		# 'method=fd' tells OpenMDAO to use FiniteDifference
		self.declare_partials("*", "*", method="fd")

	def compute(self, inputs, outputs):
		chamber_pressure = inputs["chamber_pressure"][0]
		mixture_ratio    = inputs["mixture_ratio"][0]
		expansion_ratio  = inputs["expansion_ratio"][0]

		cea = self.options["cea"]

		cstar = cea.get_Cstar(
			Pc=chamber_pressure,
			MR=mixture_ratio
		)

		isp = cea.get_Isp(
			Pc=chamber_pressure,
			MR=mixture_ratio,
			eps=expansion_ratio
		)

		outputs["cstar"] = cstar
		outputs["isp"]   = isp
		# outputs['thrust'] = 1200.0 # placeholder
