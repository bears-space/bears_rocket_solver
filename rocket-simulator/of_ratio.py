#!/usr/bin/env python
"""
@author: Andrii
@date: 28.07.2026
"""

#region Imports
import json
import numpy        as np
import openmdao.api as om
import rocketcea

from dataclasses           import dataclass
from rocketcea.cea_obj     import CEA_Obj, add_new_fuel, add_new_oxidizer, add_new_propellant
from rocketcea.input_cards import oxCards, fuelCards
#endregion

#region Datatypes
@dataclass(frozen=True)
class Reactant:
	reactype: str
	name: str
	mass_fraction: float
	formula_parts: list[dict[str, float]]
	temperature: float
	enthalpy: float
	enthalpy_units: str
	density: float
	density_units: str
#endregion

#region Helper functions
def compile_formula(formula_parts: list[dict[str, int]]) -> dict[str, int]:
	result: dict[str, int] = {}
	for part in formula_parts:
		for k, v in part.items():
			result[k] = result.get(k, 0) + v
	return result

def reactant_card(
	reactant: dict,
	reactype: str = "propellant",
	fraction: float = 100.0
) -> str:
	formula = compile_formula(reactant['formula_parts'])

	formula_comp = [ f"{atom} {float(count)}"
		             for atom, count in formula.items() ]

	formula_str = " ".join(formula_comp)

	lines = []

	line1 = [
		f"{reactype} "
		f"{reactant['name']} "
		f"{formula_str} "
		f"wt%={fraction}"
	]
	lines.append(" ".join(line1))

	line2 = [
		f"h,{reactant['enthalpy_units']}={reactant['enthalpy']} "
		f"t(k)={reactant['temperature']}"
	]
	lines.append(" ".join(line2))

	return "\n".join(lines)

"""
# Hf: kJ/mol -> cal/mol (CEA standard)
# 1 kJ = 239.006 cal
h_cal_mol = comp['Hf'] * 239.006
"""

def gencard(components: list[dict], reactype: str) -> str:
	"""Generate the appropriate reactant card from a dictionary"""

	wt_total = sum(comp['mass_fraction'] for comp in components)

	if len(components) == 1:
		return reactant_card(component[0], reactype=reactype)
	elif len(components) > 1:
		cards = []
		for comp in components:
			wt = (comp['mass_fraction'] / wt_total) * 100.0
			# NOTE: Compontent weights must add up to 100.0 for CEA

			cards.append(reactant_card(comp, reactype=reactype, fraction=wt))

		return "\n".join(cards)

def parse_reactants(data: list[dict]) -> list:
	"""
	Parse a reactant table to the corresponding oxidizer and fuel name strings.

	If either does not exist in the CEA library, it is created with the
	appropriate card.
	"""

	ret = []; cs = []
	for reactype in data.keys():
		match reactype:
			case "oxid": cards = oxCards
			case "fuel": cards = fuelCards

		reactants = data[reactype]
		rname = "_".join([reac['name'] for reac in reactants])

		if rname not in cards:
			card = gencard(reactants, reactype=reactype)
			add_new_fuel(rname, card)

			cs.append(card)

		ret.append(rname)

	return ret
	
#endregion

#region Optimization component
class OFComponent(om.ExplicitComponent):

	def __init__(self, cea: CEA_Obj, **kwargs):
		super().__init__(**kwargs)

		# Initialize the CEA object internally
		self.cea = cea

	def setup(self):
		# Input: Mixture ratio
		self.add_input('mixture_ratio', val=2.0)

		# Output: Characteristic velocity (m/s)
		self.add_output('cstar', val=1500.0)

	def setup_partials(self):
		# Declare partial derivatives
		# 'method=fd' tells OpenMDAO to use FiniteDifference
		self.declare_partials('cstar', 'mixture_ratio', method='fd')

	def compute(self, inputs, outputs):
		cstar = self.cea.get_Cstar(
			Pc  = 35.0, # Chamber pressure
			MR  = inputs['mixture_ratio'][0]
			#eps = 40.0, # Nozzle expansion area ratio
		)
		outputs['cstar'] = cstar
#endregion

#region Main
def main():
	#region Inputs
	with open("inputs/reactants.json", "r") as retrieved:
		data = json.load(retrieved)
		rnames = parse_reactants(data) 
	#endregion

	print(rnames)

	fname = rnames[0]
	oname = rnames[1]

	cea = CEA_Obj(oxName=oname, fuelName=fname)

	prob = om.Problem()

	prob.model.add_subsystem(
		'cstar_calc',
		OFComponent(cea=cea),
		promotes=['*']
	)

	prob.driver = om.ScipyOptimizeDriver()
	prob.driver.options['optimizer'] = 'SLSQP'

	prob.model.add_design_var('mixture_ratio', lower=1.0, upper=10.0)
	prob.model.add_objective('cstar', scaler=-1.0)

	prob.setup()
	prob.set_val('mixture_ratio', 2.0)
	prob.run_driver()

	print(f"Optimal MR: {prob.get_val('mixture_ratio')[0]}")
	print(f"Max cstar: {prob.get_val('cstar')[0]}")
#endregion

if __name__=="__main__": main()
