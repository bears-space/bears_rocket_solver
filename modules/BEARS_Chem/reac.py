#region Imports
from typing         import Optional
from modules.Config import ReactantConfig
#endregion

class Reactant:
	reactype       : str
	name           : str
	mass_fraction  : float
	formula_parts  : list[dict[str, float]]
	formula        : dict[str, float]
	temperature    : Optional[float]
	enthalpy       : Optional[float]
	enthalpy_units : Optional[str]
	density        : Optional[float]
	density_units  : Optional[str]

	def __init__(self, reacdict: dict):
		"""Construct a Reactant object from a dictionary"""

		# Required reactant parameters
		self.reactype      = reacdict["reactype"]
		self.name          = reacdict["name"]
		self.formula_parts = reacdict["formula_parts"]

		# Optional
		self.mass_fraction  = reacdict.get("mass_fraction",  100.0)
		self.temperature    = reacdict.get("temperature",    298.15)
		self.enthalpy       = reacdict.get("enthalpy")
		self.enthalpy_units = reacdict.get("enthalpy_units", "cal/mol")
		self.density        = reacdict.get("density")
		self.density_units  = reacdict.get("density_units")

		self.compile_formula()

	@classmethod
	def from_config(cls, cfg: ReactantConfig) -> "Reactant":
		return cls({
			"name"           : cfg.name,
			"reactype"       : cfg.reactype,
			"formula_parts"  : list(cfg.formula_parts),
			"mass_fraction"  : cfg.mass_fraction,
			"temperature"    : cfg.temperature_k,
			"enthalpy"       : cfg.enthalpy,
			"enthalpy_units" : cfg.enthalpy_units,
			"density"        : cfg.density,
			"density_units"  : cfg.density_units,
		})

	def compile_formula(self):
		"""
		Compile the formula components as specified in the JSON input into a
		complete formula
		"""
		self.formula: dict[str, float] = {}
		for part in self.formula_parts:
			for k, v in part.items():
				self.formula[k] = self.formula.get(k, 0) + v

	def get_density_si(self) -> float:
		"""Return density in kg/m^3"""
		if self.density is None:
			return 1000.0
		if self.density_units in ["g/cm^3", "g/cc", "g/cm3"]:
			return self.density * 1000.0
		return self.density

	def convert_enth_units(self, eu_out: str):

		# TODO complete the list of conversions/add a better conversion method

		j_to_cal = 0.2390057361  # 1 J = 0.239006 cal

		if self.enthalpy is not None:
			match (self.enthalpy_units, eu_out):
				case ("j/mol", "cal/mol"):
					self.enthalpy = self.enthalpy * j_to_cal
					self.enthalpy_units = "cal/mol"
				case ("kj/mol", "cal/mol"):
					self.enthalpy = self.enthalpy * 1e3 * j_to_cal
					self.enthalpy_units = "cal/mol"
				case ("cal/mol", "j/mol"):
					self.enthalpy = self.enthalpy / j_to_cal
					self.enthalpy_units = "j/mol"
				case ("cal/mol", "kj/mol"):
					self.enthalpy = self.enthalpy / 1e3 / j_to_cal
					self.enthalpy_units = "kj/mol"
