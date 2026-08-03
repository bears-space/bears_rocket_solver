#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created on Thu Jun 11 22:20:05 2026

@author: Robert
"""

#region Imports
import json
import cea
import numpy as np

from dataclasses import dataclass, replace
from typing import Tuple, List, Dict, Any

"""
From: Andrii

There is no reason to reinvent the wheel with custom optimizers here given the
wide availability of SciPy and its library of optimization functions, and
performance should improve since those have long been polished and refined. In
our case of multi-dimensional optimization with a complex cost landscape, we
need a global optimization function. SciPy's ``differential_evolution`` is a
stochastic global optimizer that should work well enough here
"""
from scipy.optimize import differential_evolution
#endregion

#region Dataclasses
"""
From: Andrii

In this section, I wanted to group together all the arguments required for
computing the Isp. The most reasonable way to do this was to break them down
into three classes:

- Since the ambition is to be able to "turn on/off" the optimization of
  particular rocket variables, such as the supersonic area ratio ``supar`` in
  the case of this file, the optimizable variables are grouped into the
  ``ModelParams`` class.

- Some variables are computed from the input reactant mixture and will not be
  optimized for. These are grouped into ``FixedParams``.

- Purely technical variables like the ``RocketSolver`` instance are conained
  into the ``SolverParams`` class.
"""

@dataclass(frozen=True)
class ModelParams:
	"""
	Parameters that may or may not be optimized.

	Optimization of individual parameters of this class can be enabled or
	disabled the optimization adapter class.
	"""
	tank_pressure: float
	pressure_ratio: float
	of_ratio: float
	subar: float
	supar: float

	# Nicer printouts
	def __str__(self):
		spacer = "\t"
		return f"ModelParams(\n" \
		       f"{spacer}tank_pressure:  {self.tank_pressure}\n" \
		       f"{spacer}pressure_ratio: {self.pressure_ratio}\n" \
		       f"{spacer}of_ratio:       {self.of_ratio}\n" \
		       f"{spacer}subar:          {self.subar}\n" \
		       f"{spacer}supar:          {self.supar})"

@dataclass(frozen=True)
class FixedParams:
	"""
	Fixed and pre-computed parameters that that will not be optimized
	"""
	weights: list[float]
	hc: float

@dataclass(frozen=True)
class SolverParams:
	"""
	Internal technical parameters
	"""
	solver: cea.RocketSolver
	solution: cea.RocketSolution
#endregion

#region Optimization setup
"""
From: Andrii

This is a replacement for Robert's custom optimization function intended to be
used with SciPy's standard "off-the-shelf" global optimization functions.

We are optimizing some set of input parameters (supersonic area ratio
``supar``, oxidizer-fuel ratio ``of_ratio, etc.) with respect to a target value
that is computed from those parameters, in this case the specific impulse
``I_sp``. Consider these as a "coordinate" space and a "target" space of some
"cost" function:

  f_cost : C -> T

  f_cost(supar, ...) = I_sp

in this case being ``C = (supar: float, ...)``, and ``T = I_sp: float``. Our
actual cost function also requires parameters that are not to be optimized (as
mentioned in the previous section), so it looks more like this:

  f_cost : (C, P) -> T

where ``C`` is as before and ``P = (hc: float, ...)`` is the tuple of
non-optimized constants that our function takes.

The ``OptimizationAdater`` class wraps our true cost function of the three
container classes and turns it into a function of only our optimizable
parameters.

This class setup is not very intuitive, but the advantage of this is that we
can easily turn optimization of specific variables on and off, and can even
optimize multiple variables at once, so with minor changes we can replace
``of_optimizer.py`` as well
"""

def f_cost(
	params_M: ModelParams,
	params_F: FixedParams,
	params_S: SolverParams
) -> float:
	"""
	The cost function for the global optimization algorithm
	"""

	# The internal CEA solver routine that we unpack all the packaged
	# parameters into
	params_S.solver.solve(
		params_S.solution,
		params_F.weights,
		params_M.tank_pressure,
		params_M.pressure_ratio,
		subar = params_M.subar,
		# Sometimes the solver breaks if ``supar`` isn't forced to a ``float``
		supar = float(params_M.supar),
		hc    = params_F.hc,
		iac   = True
	)

	# We return the _negative_ specific impulse because the optimization
	# functions attempt to _minimize_ the cost function
	return -params_S.solution.Isp[4]

class OptimizationAdapter:
	"""
	The optimization adapter class is used to optimize with respect to only
	some of the cost function variables.

	Args:
		params_M (ModelParams): Model parameters, some of which will be
			optimized.
		params_F (FixedParams): Fixed/pre-computed parameters which will not be
			optimized.
		params_S (SolverParams): Technical parameters.
		active_keys (list[str]): List of the parameters that we want to
			optimize. These will be passed to the optimization functions, while
			others will remain fixed in the optimization procedure.
		bounds_map (dict[str, tuple[float, float]]): Table of parameter bounds.
			Requires specific bounds on all parameters, including those that
			haven't been enabled in ``active_keys``
	"""
	def __init__(self,
		params_M: ModelParams,
		params_F: FixedParams,
		params_S: SolverParams,
		active_keys: list[str],
		bounds_map: dict[str, tuple[float, float]]
	):
		self.params_M = params_M
		self.params_F = params_F
		self.params_S = params_S
		self.active_keys = active_keys

		# Select bounds for only the parameters to be optimized
		self.bounds = [bounds_map[k] for k in active_keys]
	
	def __call__(self, x):
		updates = {key: val for key, val in zip(self.active_keys, x)}
		print(updates)
		params_current = replace(self.params_M, **updates)

		return f_cost(params_current, self.params_F, self.params_S)
#endregion

#region Helper functions
def compile_formula(formula_parts: list[dict[str, int]]) -> dict[str, int]:
	"""
	Helper function to sum up reactant components from a human-readable
	chemical component list
	"""
	result: Dict[str, int] = {}
	for part in formula_parts:
		for k, v in part.items():
			result[k] = result.get(k, 0) + v
	return result

def parse_reactant(reac: dict) -> None:
	"""
	Append the CEA Reactant object and fuel/oxidant masses
	to the reactant table.

	Args:
		reac (dict): Table of reactant parameters
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

def weights_and_hc(
	of_ratio: float,
	reactants: list[dict],
	mixture: cea.Mixture
) -> tuple[list[float], float]:
	"""
	Compute the weights and heat of combustion from the specified reactant
	mixture and oxidizer-fuel ratio.

	Args:
		of_ratio (float): Oxidizer-fuel ratio
		ractants (list[dict]): List of reactant data in dictionaries. This list
			is modified during execution: each reactant's weights are stored in
			its corresponding table.
		mixture (cea.Mixture): the CEA Mixture object produced from the
			reactants list

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
#endregion

#region Main
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

	reac = [r["obj"] for r in reactants] # list of Reactant objects
	mixture = cea.Mixture(reac)
	products = cea.Mixture(reac, products_from_reactants=True)

	weights, hc = weights_and_hc(rocketpar["of_ratio"], reactants, mixture)

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

	bounds = {
		"tank_pressure"  : (rocketpar["tank_pressure_min"],  rocketpar["tank_pressure_max"] ),
		"pressure_ratio" : (rocketpar["pressure_ratio_min"], rocketpar["pressure_ratio_max"]),
		"subar"          : (rocketpar["subar_min"],          rocketpar["subar_max"]         ),
		"supar"          : (rocketpar["supar_min"],          rocketpar["supar_max"]         ),
		"of_ratio"       : (rocketpar["of_ratio_min"],       rocketpar["of_ratio_max"]      ),
	}
	#endregion

	#region Optimization
	# Only these parameters will be optimized
	dynamic_keys = ["supar"]

	# Prepare the adapter with the selected keys
	bridge = OptimizationAdapter(mdl, fix, slv, dynamic_keys, bounds)

	# This is the crux of the algorithm, we use the ``differential_evolution``
	# global optimizer with the selected paramters
	result = differential_evolution(
		bridge,
		bridge.bounds,
		strategy = "best1bin",
		polish = True
	)
	#endregion

	#region Printout
	final_updates = {k: v for k, v in zip(dynamic_keys, result.x)}
	mdl_optimized = replace(mdl, **final_updates)

	print("")
	print(f"{result}")
	print("")
	print(f"{mdl_optimized}")
	#endregion
#endregion

if __name__=="__main__": main()

"""
From: Andrii
Date: 23.07.2026

IMPORTANT: Replacing the custom optimizer has somewhat solved the performance
issue (the execution time is not instant but definitely faster than 2s), but
there seems to be a big issue with the actual optimized value of ``supar``.
Specifically, the algorithm optimizes to the maximum allowed value of
``supar``, to the maximum bound of the parameter passed to the optimizer. So,
if you specify

  "supar_max": 10.0

in ``inputs/rocket_parameters.json``, the algorithm will find that the optimal
value of ``supar`` is 10. I have tested this with maximum area ratio values as
high as 100.

This is not just an issue with the new implementation: in the old version of
this file if you allow a wider range of ``supar``s in the optimization
function, the algorithm will select the largest possible value. In my testing,
epxanding the candidate array inside the old ``suparOptimizer`` function

  candidates = [                                                              
    (BaseSupar - 2 * deviationValue, solve_for_supar(BaseSupar - 2 * deviationValue)),
    (BaseSupar -     deviationValue, solve_for_supar(BaseSupar -     deviationValue)),
    (BaseSupar +     deviationValue, solve_for_supar(BaseSupar +     deviationValue)),
    (BaseSupar + 2 * deviationValue, solve_for_supar(BaseSupar + 2 * deviationValue)),
    (BaseSupar + 3 * deviationValue, solve_for_supar(BaseSupar + 3 * deviationValue)),
    ...
  ]

the algorithm always maximizes "to the right"
"""
