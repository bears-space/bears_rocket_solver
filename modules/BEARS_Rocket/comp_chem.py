#region Imports
from openmdao.api import ExplicitComponent

from ..BEARS_Chem import BEARS_Chem
#endregion

class ChemComponent(ExplicitComponent):
	"""
	Equilibrium chamber state and specific impulse from chemistry backend

	CEA is real-valued only, so the partials are finite differences
	"""

	def initialize(self):
		# Chemistry of the propellant combination
		self.options.declare("chem", types=BEARS_Chem)

	def setup(self):
		# Chamber pressure [Pa]
		self.add_input("chamber_pressure", val=35e5, units="Pa")
		# Oxidizer over fuel mass flow [-]
		self.add_input("mixture_ratio",    val=6.0)
		# Nozzle exit over throat area [-]
		self.add_input("expansion_ratio",  val=5.0)
		# Combustion efficiency on c* and Isp [-]
		self.add_input("eta_cstar",        val=1.0)

		# Sea-level Isp, combustion losses included [s]
		self.add_output("isp",        val=200.0,  units="s")
		# Adiabatic flame temperature [K]
		self.add_output("t_chamber",  val=3000.0, units="K")
		# Ratio of specific heats of the chamber gas [-]
		self.add_output("gamma",      val=1.2)
		# Molar mass of the chamber gas [kg/mol]
		self.add_output("molar_mass", val=0.025,  units="kg/mol")

	def setup_partials(self):
		self.declare_partials(
			["isp", "t_chamber", "gamma", "molar_mass"],
			["chamber_pressure", "mixture_ratio"],
			method="fd",
			step=1e-4,
		)

		# Only Isp depends on expansion ratio; chamber state does not
		self.declare_partials(
			"isp", "expansion_ratio", method="fd", step=1e-4,
		)

	def compute(self, inputs, outputs):
		state = self.options["chem"].evaluate(
			inputs["chamber_pressure"][0],
			inputs["mixture_ratio"][0],
			inputs["expansion_ratio"][0],
		)

		outputs["isp"]        = inputs["eta_cstar"] * state.isp
		outputs["t_chamber"]  = state.t_chamber
		outputs["gamma"]      = state.gamma
		outputs["molar_mass"] = state.molar_mass
