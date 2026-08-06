#region Imports
import json

from dataclasses           import dataclass
from rocketcea.input_cards import oxCards, fuelCards
from rocketcea.cea_obj     import CEA_Obj, add_new_fuel, add_new_oxidizer
#endregion

class Reactant:
	reactype       : str
	name           : str
	mass_fraction  : float
	formula_parts  : list[dict[str, float]]
	formula        : dict[str, float]
	temperature    : float
	enthalpy       : float
	enthalpy_units : str
	density        : float
	density_units  : str

	def __init__(self, reacdict: dict):
		"""Construct a Reactant object from a JSON-parsed dictionary"""

		# Required reactant parameters
		self.reactype       = reacdict['reactype']
		self.name           = reacdict['name']
		self.formula_parts  = reacdict['formula_parts']

		# Optional
		self.mass_fraction  = reacdict.get('mass_fraction',  100.0)
		self.temperature    = reacdict.get('temperature',    298.15)
		self.enthalpy       = reacdict.get('enthalpy')
		self.enthalpy_units = reacdict.get('enthalpy_units', 'cal/mol')
		self.density        = reacdict.get('density')
		self.density_units  = reacdict.get('density_units')

		self.compile_formula()

	def compile_formula(self):
		"""
		Compile the formula components as specified in the JSON input into a
		complete formula
		"""
		self.formula: dict[str, float] = {}
		for part in self.formula_parts:
			for k, v in part.items():
				self.formula[k] = self.formula.get(k, 0) + v

	def convert_enth_units(self, eu_out: str):

		# TODO complete the list of conversions/add a better conversion method

		j_to_cal = 0.2390057361 # 1 J = 0.239006 cal
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

#region Helper functions
def reactant_card(reactant: Reactant, fraction: float = None) -> str:
	"""
	Generate a CEA propellant card for a Reactant object, specifying the `wt%`
	fraction

	See <https://rocketcea.readthedocs.io/en/latest/std_examples.html>
	"""

	f = reactant.mass_fraction
	if fraction: f = fraction

	formula_comp = [ f"{atom} {float(count)}"
		             for atom, count in reactant.formula.items() ]

	formula_str = " ".join(formula_comp)

	lines = []

	line1 = [
		f"{reactant.reactype} "
		f"{reactant.name} "
		f"{formula_str} "
		f"wt%={f}"
	]
	lines.append(" ".join(line1))

	line2 = [
		f"h,{reactant.enthalpy_units}={reactant.enthalpy} "
		f"t(k)={reactant.temperature}"
	]
	lines.append(" ".join(line2))

	return "\n".join(lines)

def gencard(components: list[Reactant]) -> str:
	"""
	Generate a CEA propellant card from a list of reactants, weighing each
	reactant appropriately according to its `mass_fraction` field

	Same thing as `reactant_card` but for lists

	See <https://rocketcea.readthedocs.io/en/latest/std_examples.html>
	"""

	rt = components[0].reactype
	if not all(r.reactype == rt for r in components):
		raise ValueError("Can only generate a composite card " +
		                 "for reactants of the same type")

	wt_total = sum(comp.mass_fraction for comp in components)

	if len(components) == 1:
		return reactant_card(component[0], fraction=100.0)
	elif len(components) > 1:
		cards = []
		for comp in components:
			wt = (comp.mass_fraction / wt_total) * 100.0
			# NOTE: Compontent weights must add up to 100.0 for CEA

			cards.append(reactant_card(comp, fraction=wt))

		return "\n".join(cards)
#endregion

def parse_reactants(data: dict[str, list[dict]]) -> tuple[str, str]:
	"""
	Parse a dictionary of fuel and oxidizer mixtures to the corresponding
	reactant names

	If a reactant or mixture does not exist in the RocketCEA propellant
	database, it is created with the appropriate card

	Returns the oxidizer and fuel names for passing to `CEA_Obj`
	"""

	reac_cards = { 'oxid': oxCards, 'fuel': fuelCards }

	rnames: dict[str, str] = {}
	for rtype in ['oxid', 'fuel']:
		if not all(r['reactype'] == rtype for r in data[rtype]):
			raise ValueError("Can only generate a composite card " +
			                 "for reactants of the same type")

		reactants = list(map(Reactant, data[rtype]))
		rname = '_'.join([reac.name for reac in reactants])

		card = reac_cards[rtype]
		if rname not in card:
			card = gencard(reactants)
			add_new_fuel(rname, card)

		rnames[rtype] = rname

	return rnames['oxid'], rnames['fuel']
