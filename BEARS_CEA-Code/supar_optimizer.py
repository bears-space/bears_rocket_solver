#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 11 22:20:05 2026

@author: Robert

im Folgenden wird die ungefähre Funktionsweisre der optimizer erklärt:
- Basiswert geht rein -> Basis-Isp
- Werte um Basiswert -> Isp-Werte um Basis
- Isps werden abgleichen
- wenn einer der Werte um Base-Isp > Base-Isp -> wird zu neuem Basiswert

Das wird wiederholt, bis die "Spitze" gefunden wurde, woraufhin der Bereich um
Faktor 10 verkleinert wird Das wird so oft wiederholt, wie man zu optimierende
Nachkommastellen (optimizedDigits_X) angegeben hat

Anders als ein Line-Sweep ist diese Methode jedoch anfällig für lokale Maxima,
was ich durch eine relativ große Area versucht habe, zu minimieren
"""

import json
import cea
import numpy as np

from dataclasses import dataclass, replace
from typing import Tuple, List, Dict

from scipy.optimize import differential_evolution


# Parameters that may or may not be optimized
# Optimization of individual parameters of this class can be enabled or
# disabled via the adapter class, see below
@dataclass(frozen=True)
class ModelParams:
	tank_pressure: float
	pressure_ratio: float
	of_ratio: float
	subar: float
	supar: float

# Fixed and pre-computed parameters that that will not be optimized
@dataclass(frozen=True)
class FixedParams:
	weights: List[float]
	hc: float

# Technical parameters
@dataclass(frozen=True)
class SolverParams:
	solver: cea.RocketSolver
	solution: cea.RocketSolution


def f_cost(
	params_M: ModelParams,
	params_F: FixedParams,
	params_S: SolverParams
) -> float:
	"""
	The partial cost function for the global optimization algorithm
	"""
	params_S.solver.solve(
		params_S.solution,
		params_F.weights,
		params_M.tank_pressure,
		params_M.pressure_ratio,
		subar = params_M.subar,
		supar = float(params_M.supar),
		hc = params_F.hc,
		iac = True
	)

	return -params_S.solution.Isp[4]

class OptimizationAdapter:
	def __init__(self,
		params_M: ModelParams,
		params_F: FixedParams,
		params_S: SolverParams,
		active_keys: list,
		bounds_map: dict
	):
		self.params_M = params_M
		self.params_F = params_F
		self.params_S = params_S
		self.active_keys = active_keys
		self.bounds = [bounds_map[k] for k in active_keys]
	
	def __call__(self, x):
		updates = {key: val for key, val in zip(self.active_keys, x)}
		params_current = replace(self.params_M, **updates)

		return f_cost(params_current, self.params_F, self.params_S)


def compile_formula(formula_parts: List[Dict[str, int]]) -> Dict[str, int]:
	"""Sum up reactant components"""
	result: Dict[str, int] = {}
	for part in formula_parts:
		for k, v in part.items():
			result[k] = result.get(k, 0) + v
	return result

def parse_reactant(reac: dict):
	"""
	Append the CEA Reactant object and fuel/oxidant masses
	to the reactant table.

	Modifies the original Dict.
	"""
	# Fuel and oxidant weights
	reac["fuel_mass"] = reac["density"] * reac["fuel_volume"]
	reac["oxy_mass"]  = reac["density"] * reac["oxidant_volume"]

	# CEA Reactant object
	reac["obj"] = cea.Reactant(
		name = reac["name"],
		formula = compile_formula(reac["formula_parts"]),

		# Not specifying enthalpy here for now because it changes the result of
		# heat of combusion calculation compared to the old version
		enthalpy = None, # reac.get("enthalpy", None),
		enthalpy_units = None, # reac.get("enthalpy_units", None),

		temperature = reac["temperature"]
	)

def heat_of_combustion(
	of_ratio: float,
	reactants: list,
	mixture: cea.Mixture
) -> Tuple[List[float], float]:
	"""
	Compute the weights and heat of combustion from the oxidizer-fuel ratios of
	the provided list of reactants.

	Args:
		of_ratio (float): Oxidizer to fuel ratio
		ractants (list): List of reactant data in dictionaries. This list is
			modified during execution: each reactant's weights are stored in
			its corresponding ``dict``.

	Returns:
		The weights as a list of ``float``s, heat of combusion as ``float``.
	"""
	weights = mixture.of_ratio_to_weights(
		np.array([r["oxy_mass"]  for r in reactants]),
		np.array([r["fuel_mass"] for r in reactants]),
		of_ratio
	)

	for r, w in zip(reactants, weights): r["weight"] = w

	hc = mixture.calc_property(
		cea.ENTHALPY,
		np.array([r["weight"]      for r in reactants]),
		np.array([r["temperature"] for r in reactants])
	) / cea.R

	return weights, hc


def main():
	#region Inputs
	with open("inputs/reactants.json", "r") as retrieved:
		data = json.load(retrieved)
		reactants = data["reactants"]
		for r in reactants:
			parse_reactant(r) 

	with open("inputs/rocket_parameters.json", "r") as retrieved:
		rocketpar = json.load(retrieved)

	for r in reactants: print(f"{r}\n")
	#endregion

	reac = [r["obj"] for r in reactants] # list of Reactant objects
	mixture = cea.Mixture(reac)
	products = cea.Mixture(reac, products_from_reactants=True)

	weights, hc = heat_of_combustion(rocketpar["of_ratio"], reactants, mixture)

	solver = cea.RocketSolver(products, reactants=mixture)
	solution = cea.RocketSolution(solver)

	slv = SolverParams(solver=solver, solution=solution)
	fix = FixedParams(weights=weights, hc=hc)
	mdl = ModelParams(
		tank_pressure = rocketpar["tank_pressure"],
		pressure_ratio = rocketpar["pressure_ratio"],
		of_ratio = rocketpar["of_ratio"],
		subar = rocketpar["subar"],
		supar = rocketpar["supar"]
	)

	dynamic_keys = ["supar"]

	dynamic_bounds = {
		"tank_pressure"  : (rocketpar["tank_pressure_min"],  rocketpar["tank_pressure_max"] ),
		"pressure_ratio" : (rocketpar["pressure_ratio_min"], rocketpar["pressure_ratio_max"]),
		"subar"          : (rocketpar["subar_min"],          rocketpar["subar_max"]         ),
		"supar"          : (rocketpar["supar_min"],          rocketpar["supar_max"]         ),
		"of_ratio"       : (rocketpar["of_ratio_min"],       rocketpar["of_ratio_max"]      ),
	}

	bridge = OptimizationAdapter(mdl, fix, slv, dynamic_keys, dynamic_bounds)

	result = differential_evolution(
		bridge,
		bridge.bounds,
		strategy="best1bin",
		polish=True
	)

	print(f"{result.success}")
	print("")
	print(f"{result}")

	return

	# plan ist, die Rundung später rauszunehmen und mit den exakten Werten zu
	# rechnen
	with open("inputs/cea_values.json", "r") as retrieved:
		data = json.load(retrieved)
		data["supar"] = optimizedSupar
		with open("inputs/cea_values.json", "w") as updated:
			json.dump(data, updated, indent=4)


if __name__=="__main__": main()
