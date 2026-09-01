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

	prob.driver = om.ScipyOptimizeDriver()
	prob.driver.options["optimizer"] = "SLSQP"

	# Design variables
	if opt_mr:
		prob.model.add_design_var(
			"OptimizationVars.mixture_ratio",
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
	prob.set_val("DesignVars.diameter", 0.4)
	prob.set_val("DesignVars.tank_pressure", 30e5)
	prob.set_val("DesignVars.chamber_pressure", 35.0, units="bar")
	prob.set_val("DesignVars.nozzle_expansion_ratio", 40.0)

	prob.set_val("Propulsion.thrust", 3000.0)

	# Optimization initial values
	prob.set_val("OptimizationVars.mixture_ratio", 6.0)
	prob.set_val("OptimizationVars.propellant_mass", 30.0)

	prob.run_driver()

	# region Output
	print("Optimized parameters:")
	print(f"m_prop:\t{prob.get_val('OptimizationVars.propellant_mass')[0]} kg")

	if opt_mr:
		print(f"MR:\t{prob.get_val('OptimizationVars.mixture_ratio')[0]}")

	print("\nResults:")
	print(f"t_burn:\t{prob.get_val('burn_time')[0]} s")
	print(f"h_max: \t{prob.get_val('apogee')[0]} m")
	print(f"Isp:   \t{prob.get_val('Propulsion.isp')[0]} s")

	print("\nTank parameters:")
	print(f"m_struct:\t{prob.get_val('Propulsion.m_tank_dry')[0]} kg")
	print(f"t_wall:  \t{prob.get_val('Propulsion.Tank.t_wall')[0]} m")
	print(f"l_tank:  \t{prob.get_val('Propulsion.Tank.l_tank')[0]} m")

	# Dump all computed component outputs to a file
	with open("outputs/outputs.txt", mode="wt") as f:
		f.write("\nTank\n")
		f.write(f"m_struct:\t{prob.get_val('Propulsion.Tank.m_tank_dry')[0]} kg\n")
		f.write(f"t_wall:\t{prob.get_val('Propulsion.Tank.t_wall')[0]} m\n")
		f.write(f"l_tank:\t{prob.get_val('Propulsion.Tank.l_tank')[0]} m\n")
		f.write(f"v_internal:\t{prob.get_val('Propulsion.Tank.v_internal')[0]} m**3\n")

		f.write("\nChemistry\n")
		f.write(f"thrust:\t{prob.get_val('Propulsion.Chemistry.thrust')[0]} N\n")
		f.write(f"cstar:\t{prob.get_val('Propulsion.Chemistry.cstar')[0]} m/s\n")
		f.write(f"isp:\t{prob.get_val('Propulsion.Chemistry.isp')[0]} s\n")

		f.write("\nMass\n")
		f.write(f"initial_mass:\t{prob.get_val('Mass.initial_mass')[0]} kg\n")
		f.write(f"dry_mass:\t{prob.get_val('Mass.dry_mass')[0]} kg\n")

		f.write("\nTrajectory\n")
		f.write(f"burn_time:\t{prob.get_val('Trajectory.burn_time')[0]} s\n")
		f.write(f"apogee:\t{prob.get_val('Trajectory.apogee')[0]} m\n")

	# Draw all the connectivity graphs
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
