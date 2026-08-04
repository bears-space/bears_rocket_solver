#!/usr/bin/env python
"""
@author: Andrii
@date: 28.07.2026
"""

#region Imports
import json
import numpy        as np
import openmdao.api as om

from scipy.integrate   import solve_ivp
from scipy.interpolate import interp1d
from scipy.constants   import g
from rocketcea.cea_obj import CEA_Obj
from openmdao.visualization.graph_viewer import GraphViewer

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

	# Design variables
	#prob.model.add_design_var('mixture_ratio',   lower=1.0, upper=10.0)
	prob.model.add_design_var('propellant_mass', lower=1.0, upper=100.0, ref=10.0)

	# Constraints
	prob.model.add_constraint('apogee', equals=3000.0, ref=3000.0)

	# Objectives
	#prob.model.add_objective('prop.cstar', scaler=-1.0)
	prob.model.add_objective('propellant_mass')

	prob.setup()

	# Dynamic variables
	prob.set_val('mass.structural_coefficient', val=0.35)

	prob.set_val('prop.chamber_pressure', 35.0)
	prob.set_val('prop.mixture_ratio',     6.0)
	prob.set_val('prop.expansion_ratio',  40.0)
	prob.set_val('prop.thrust',           20.0)

	# Optimization initial values
	prob.set_val('propellant_mass', 1.0)
	prob.set_val('payload_mass',    1.0)

	prob.run_driver()

	print(f"Req propellant: {prob.get_val('propellant_mass')[0]} kg")
	print(f"Final apogee:   {prob.get_val('apogee')[0]} m")

	viewer = GraphViewer(prob.model)
	for graph_type in ['dataflow', 'tree', 'cycle']:
		viewer.write_graph(
			gtype=graph_type,
			display=False,
			show_vars=True,
			outfile=f'figures/{graph_type}.png'
		)
#endregion

if __name__=="__main__": main()
