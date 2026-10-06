#region Imports
from typing                import Optional
from rocketcea.input_cards import oxCards, fuelCards
from rocketcea.cea_obj     import CEA_Obj, add_new_fuel, add_new_oxidizer

from .reac import Reactant
#endregion

def reactant_card(reactant: Reactant, fraction: Optional[float] = None) -> str:
	"""
	Generate a CEA propellant card for a Reactant object, specifying the `wt%`
	fraction

	See <https://rocketcea.readthedocs.io/en/latest/std_examples.html>
	"""

	f = reactant.mass_fraction
	if fraction:
		f = fraction

	formula_comp = [
		f"{atom} {float(count)}" for atom, count in reactant.formula.items()
	]

	formula_str = " ".join(formula_comp)

	lines = []

	line1 = [
		f"{reactant.reactype}",
		f"{reactant.name}",
		f"{formula_str}",
		f"wt%={f}",
	]
	lines.append(" ".join(line1))

	line2 = [
		f"h,{reactant.enthalpy_units}={reactant.enthalpy}",
		f"t(k)={reactant.temperature}",
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
		raise ValueError(
			"Can only generate a composite card for reactants of the same type"
		)

	wt_total = sum(comp.mass_fraction for comp in components)

	if len(components) == 1:
		return reactant_card(components[0], fraction=100.0)
	else:
		cards = []
		for comp in components:
			wt = (comp.mass_fraction / wt_total) * 100.0
			# NOTE: Compontent weights must add up to 100.0 for CEA

			cards.append(reactant_card(comp, fraction=wt))

		return "\n".join(cards)

def bulk_density(reactants: list[Reactant]) -> float:
	"""Effective bulk density in kg/m^3 for a list of reactants"""
	wt_total = sum(r.mass_fraction for r in reactants)
	inv_rho = sum(
		(r.mass_fraction / wt_total) / r.get_density_si() for r in reactants
	)
	return 1.0 / inv_rho

def parse_reactants(data: dict[str, list[dict]]) -> tuple[str, str]:
	"""
	Parse a dictionary of fuel and oxidizer mixtures to the corresponding
	reactant names

	If a reactant or mixture does not exist in the RocketCEA propellant
	database, it is created with the appropriate card

	Returns the oxidizer and fuel names for passing to `CEA_Obj`
	"""

	reac_cards = {"oxid": oxCards, "fuel": fuelCards}

	rnames: dict[str, str] = {}
	for rtype in ["oxid", "fuel"]:
		if not all(r["reactype"] == rtype for r in data[rtype]):
			raise ValueError(
				"Can only generate a composite card "
				+ "for reactants of the same type"
			)

		reactants = list(map(Reactant, data[rtype]))
		rname = "_".join([reac.name for reac in reactants])

		card = reac_cards[rtype]
		if rname not in card:
			card = gencard(reactants)
			if rtype == "fuel": add_new_fuel(rname, card)
			else: add_new_oxidizer(rname, card)

		rnames[rtype] = rname

	return rnames["oxid"], rnames["fuel"]

def parse_densities(data: dict[str, list[dict]]) -> tuple[float, float]:
	"""
	Calculate effective bulk densities for oxidizer and fuel in kg/m^3.
	"""
	rs_ox = list(map(Reactant, data["oxid"]))
	rs_fu = list(map(Reactant, data["fuel"]))
	return bulk_density(rs_ox), bulk_density(rs_fu)
