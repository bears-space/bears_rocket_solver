#!/usr/bin/env python
"""
@author: Andrii
@date: 28.07.2026
"""

#region Imports
import json
import numpy        as np
import openmdao.api as om

from rocketcea.cea_obj import CEA_Obj

from packages.BEARS_Chem   import Reactant, parse_reactants
from packages.BEARS_Rocket import RocketGroup
#endregion

#region Main
def main():
	#region Inputs
	with open('inputs/reactants.json', 'r') as retrieved:
		data = json.load(retrieved)
		oname, fname = parse_reactants(data)
	#endregion

	cea = CEA_Obj(oxName=oname, fuelName=fname)

	prob = om.Problem()

	rocket = RocketGroup(cea=cea)
	prob.model.add_subsystem('BEARS_Rocket', rocket, promotes=['*'])

	prob.driver = om.ScipyOptimizeDriver()
	prob.driver.options['optimizer'] = 'SLSQP'

	prob.model.add_design_var('mixture_ratio', lower=1.0, upper=10.0)
	prob.model.add_objective('prop.cstar', scaler=-1.0)

	prob.setup()
	prob.set_val('mixture_ratio', 2.0)
	prob.run_driver()

	print(f"Optimal MR: {prob.get_val('mixture_ratio')[0]}")
	print(f"Max cstar: {prob.get_val('prop.cstar')[0]}")
#endregion

if __name__=="__main__": main()
