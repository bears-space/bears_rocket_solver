#!/usr/bin/env python
"""
The rocket optimization script using OpenMDAO for the framework

@author:  Andrii
@license: GPL-3.0-or-later
"""

#region Imports
import json
import os
import numpy        as np
import openmdao.api as om
import rocketcea.cea_obj as cea_obj

from scipy.integrate   import solve_ivp
from scipy.interpolate import interp1d
from scipy.constants   import g
from rocketcea.cea_obj import CEA_Obj
from openmdao.visualization.graph_viewer import GraphViewer

from modules.BEARS_Atmo   import BEARS_Atm
from modules.BEARS_Chem   import Reactant, parse_reactants, parse_densities
from modules.BEARS_Rocket import RocketGroup
#endregion

#region Main
def main():

	opt_mr = True

	#region Working directories
	work_dir = os.path.abspath("work")
	os.makedirs(work_dir, exist_ok=True)
	cea_obj.ROCKETCEA_DATA_DIR = os.path.join(work_dir, "RocketCEA")
	#endregion

	#region Inputs
	with open("inputs/reactants.json", "r") as retrieved:
		data = json.load(retrieved)
		oname, fname = parse_reactants(data)
		rho_ox, rho_fuel = parse_densities(data)
	#endregion

	atm = BEARS_Atm("isacalc")
	cea = CEA_Obj(oxName=oname, fuelName=fname)

	prob = om.Problem(reports=True, work_dir=work_dir)

	prob.model = RocketGroup(
		atm=atm,
		cea=cea,
		rho_ox=rho_ox,
		rho_fuel=rho_fuel,
	)

	prob.driver = om.ScipyOptimizeDriver()
	prob.driver.options["optimizer"] = "SLSQP"

	# Design variables
	if opt_mr:
		prob.model.add_design_var(
			"OptimizationVars.mixture_ratio",
			lower=2.0, upper=10.0, ref=6.0
		)

	prob.model.add_design_var(
		"OptimizationVars.propellant_mass", lower=1.0, upper=50.0, ref=10.0
	)

	# Constraints
	prob.model.add_constraint("apogee", equals=3100.0, ref=3100.0)

	# Objectives
	prob.model.add_objective("OptimizationVars.propellant_mass", ref=10.0)

	prob.setup()

	# Dynamic variables
	prob.set_val("DesignVars.payload_mass", 1.0)
	prob.set_val("DesignVars.diameter", 0.4)
	prob.set_val("DesignVars.tank_pressure", 30e5)
	prob.set_val("DesignVars.nozzle_expansion_ratio", 40.0)
	prob.set_val("DesignVars.injector_area", 4.5e-5)
	prob.set_val("DesignVars.injector_cd", 0.7)
	prob.set_val("DesignVars.throat_area", 5.0e-4)

	# Optimization initial values
	prob.set_val("OptimizationVars.mixture_ratio", 6.0)
	prob.set_val("OptimizationVars.propellant_mass", 15.0)

	prob.run_driver()

	#region Outputs
	print("Optimized parameters:")
	print(f"m_prop:\t{prob.get_val('OptimizationVars.propellant_mass')[0]} kg")

	if opt_mr:
		print(f"MR:\t{prob.get_val('OptimizationVars.mixture_ratio')[0]}")

	p_c = prob.get_val("Propulsion.Nozzle.p_chamber")[0]
	thrust = prob.get_val("Propulsion.thrust")[0]

	print("\nResults:")
	print(f"t_burn:\t{prob.get_val('burn_time')[0]} s")
	print(f"h_max: \t{prob.get_val('apogee')[0]} m")
	print(f"P_ch:  \t{p_c / 1e5:.2f} bar")
	print(f"Thrust:\t{thrust:.1f} N")
	print(f"Isp:   \t{prob.get_val('Propulsion.isp')[0]} s")

	print("\nTank parameters:")
	print(f"m_struct:\t{prob.get_val('Propulsion.m_tank_dry')[0]} kg")
	print(f"t_wall:  \t{prob.get_val('Propulsion.Tank.t_wall')[0]} m")
	print(f"l_tank:  \t{prob.get_val('Propulsion.Tank.l_tank')[0]} m")

	# Dump all computed variables to an output file
	with open("outputs/outputs.txt", mode="wt") as f:
		prob.model.list_outputs(
			val=True,
			units=True,
			hierarchical=True,
			out_stream=f,
		)

	# Draw all the connectivity graphs
	viewer = GraphViewer(prob.model)
	for graph_type in ["dataflow", "tree", "cycle"]:
		viewer.write_graph(
			gtype=graph_type,
			display=False,
			show_vars=True,
			outfile=f"figures/{graph_type}.png",
		)
	#endregion
#endregion

if __name__ == "__main__": main()
