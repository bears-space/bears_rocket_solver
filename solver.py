#!/usr/bin/env python
"""
The rocket optimization script using OpenMDAO for the superstructure

@author:  Andrii
@license: GPL-3.0-or-later
"""

# region Imports
import json
import numpy        as np
import openmdao.api as om

from scipy.integrate   import solve_ivp
from scipy.interpolate import interp1d
from scipy.constants   import g
from rocketcea.cea_obj import CEA_Obj
from openmdao.visualization.graph_viewer import GraphViewer

from modules.BEARS_Atmo   import BEARS_Atm
from modules.BEARS_Chem   import Reactant, parse_reactants
from modules.BEARS_Rocket import RocketGroup
# endregion

# region Main
def main():

	opt_mr = True

	# region Inputs
	with open("inputs/reactants.json", "r") as retrieved:
		data = json.load(retrieved)
		oname, fname = parse_reactants(data)
	# endregion

	atm = BEARS_Atm("isacalc")
	cea = CEA_Obj(oxName=oname, fuelName=fname)

	prob = om.Problem()

	prob.model = RocketGroup(atm=atm, cea=cea)

	#prob.model.add_subsystem("BEARS_Rocket", rocket, promotes=["*"])

	prob.driver = om.ScipyOptimizeDriver()
	prob.driver.options["optimizer"] = "SLSQP"

	# Design variables
	if opt_mr:
		prob.model.add_design_var(
			"OptimizationVars.propellant_mixture_ratio",
			lower=1.0, upper=10.0, ref=2.0
		)

	prob.model.add_design_var(
		"OptimizationVars.propellant_mass", lower=1.0, upper=100.0, ref=30.0
	)

	# Constraints
	prob.model.add_constraint("apogee", equals=3100.0)

	# Objectives
	prob.model.add_objective("OptimizationVars.propellant_mass")

	prob.setup()

	# Dynamic variables
	prob.set_val("DesignVars.payload_mass", 1.0)

	prob.set_val("Mass.structural_coefficient", 0.01 * 30)  # percentages

	prob.set_val("Trajectory.diameter", 0.4)

	prob.set_val("Propulsion.chamber_pressure", 35.0)
	prob.set_val("Propulsion.expansion_ratio", 40.0)
	prob.set_val("Propulsion.thrust", 3000.0)

	# Optimization initial values
	prob.set_val("OptimizationVars.propellant_mixture_ratio", 6.0)
	prob.set_val("OptimizationVars.propellant_mass", 30.0)

	prob.run_driver()

	# region Output
	print("Optimized parameters:")
	print(f"m_prop:\t{prob.get_val('OptimizationVars.propellant_mass')[0]} kg")

	if opt_mr:
		print(f"MR:\t{prob.get_val('OptimizationVars.propellant_mixture_ratio')[0]}")

	print("\nResults:")
	print(f"t_burn:\t{prob.get_val('burn_time')[0]} s")
	print(f"h_max:\t{prob.get_val('apogee')[0]} m")
	print(f"Isp:\t{prob.get_val('Propulsion.isp')[0]} m/s")

	viewer = GraphViewer(prob.model)
	for graph_type in ["dataflow", "tree", "cycle"]:
		viewer.write_graph(
			gtype=graph_type,
			display=False,
			show_vars=True,
			outfile=f"figures/{graph_type}.png",
		)
	# endregion
# endregion

if __name__ == "__main__": main()
