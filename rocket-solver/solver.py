#!.env/bin/python
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
from modules.BEARS_Rocket import TestStandProblem, RocketLaunchProblem
#endregion

#region Main
def main():

	#region Working directories
	work_dir = os.path.abspath("work")
	os.makedirs(work_dir, exist_ok=True)
	cea_obj.ROCKETCEA_DATA_DIR = os.path.join(work_dir, "RocketCEA")
	#endregion

	#region Inputs
	with open("inputs/reactants.json", "r") as f:
		data = json.load(f)
		oname, fname = parse_reactants(data)
		rho_ox, rho_fuel = parse_densities(data)

	atm = BEARS_Atm("isacalc")
	cea = CEA_Obj(oxName=oname, fuelName=fname)
	#endregion

	#region Rocket optimization
	prob_rocket = RocketLaunchProblem(
		atm=atm,
		cea=cea,
		rho_ox=rho_ox,
		rho_fuel=rho_fuel,
		payload_mass=10.0,
		target_apogee=3100.0,
		reports=True,
		work_dir=work_dir,
	)
	prob_rocket.setup()
	res = prob_rocket.run()

	PRINT_FMT = "8.3f"

	print("Optimizing the rocket...")
	print("")
	print(f"Optimized m_prop:     \t{res['m_prop_kg']:{PRINT_FMT}} kg")
	print(f"Optimized A_inj:      \t{res['a_inj_mm2']:{PRINT_FMT}} mm²")
	print(f"Optimized A_throat:   \t{res['a_throat_cm2']:{PRINT_FMT}} cm²")
	print(f"Optimized MR:         \t{res['mr']:{PRINT_FMT}}")
	print("")
	print(f"Apogee:               \t{res['apogee_m']:{PRINT_FMT}} m")
	print(f"Burn time:            \t{res['burn_time_s']:{PRINT_FMT}} s")
	print(f"Liftoff thrust:       \t{res['thrust_N']:{PRINT_FMT}} N")
	print(f"Liftoff Isp:          \t{res['isp_s']:{PRINT_FMT}} s")
	print(f"Chamber pressure:     \t{res['p_chamber_bar']:{PRINT_FMT}} bar")
	print(f"Injector ΔP:          \t{res['delta_p_bar']:{PRINT_FMT}} bar")
	print("")
	print(f"Dry mass:             \t{res['m_dry_kg']:{PRINT_FMT}} kg")
	print(f"Total mass at liftoff:\t{res['m_initial_kg']:{PRINT_FMT}} kg")

	# Dump all computed variables to an output file
	with open("outputs/rocket.txt", mode="wt") as f:
		prob_rocket.model.list_outputs(
			val=True,
			units=True,
			hierarchical=True,
			out_stream=f,
		)

	# Draw all the connectivity graphs
	viewer = GraphViewer(prob_rocket.model)
	for graph_type in ["dataflow", "tree", "cycle"]:
		viewer.write_graph(
			gtype=graph_type,
			display=False,
			show_vars=True,
			outfile=f"figures/rocket_{graph_type}.png",
		)

	m_prop_opt   = res['m_prop_kg']
	mr_opt       = res['mr']
	a_inj_opt    = res['a_inj_mm2']
	a_throat_opt = res['a_throat_cm2']
	#endregion

	print("--------")

	#region Test stand
	prob_stand = TestStandProblem(
		cea=cea,
		rho_ox=rho_ox,
		rho_fuel=rho_fuel,
		reports=False,
	)

	prob_stand.setup()

	prob_stand.set_opt_vars(
		#m_prop_kg=m_prop_opt,
		mr=mr_opt,
		a_inj_mm2=a_inj_opt,
		a_throat_cm2=a_throat_opt,
	)

	res = prob_stand.run()

	print("Simulating test stand...")
	print("")
	print(f"PT1 (N2O supply pressure):      \t{res['PT1_N2O_supply_bar']:{PRINT_FMT}} bar")
	print(f"TC1 (N2O supply temperature):   \t{res['TC1_N2O_supply_K']:{PRINT_FMT}} K")
	print("")
	print(f"PT2 (run tank feed temperature):\t{res['PT2_run_tank_bar']:{PRINT_FMT}} bar")
	print(f"TC2 (run tank liquid temp):     \t{res['TC2_run_liquid_K']:{PRINT_FMT}} K")
	print("")
	print(f"PT3 (chamber pressure):         \t{res['PT3_chamber_bar']:{PRINT_FMT}} bar")
	print(f"TC3 (chamber flame temp):       \t{res['TC3_chamber_temp_K']:{PRINT_FMT}} K")
	print("")
	print(f"PT4 (N2 supply pressure):       \t{res['PT4_N2_supply_bar']:{PRINT_FMT}} bar")
	print(f"TC4 (N2 supply pressure):       \t{res['TC4_run_dome_K']:{PRINT_FMT}} K")
	print("")
	print(f"ΔP:                             \t{res['delta_p_feed_bar']:{PRINT_FMT}} bar")
	print(f"Thrust:                         \t{res['thrust_N']:{PRINT_FMT}} N")
	print(f"Isp:                            \t{res['isp_s']:{PRINT_FMT}} s")

	# Dump all computed variables to an output file
	with open("outputs/teststand.txt", mode="wt") as f:
		prob_stand.model.list_outputs(
			val=True,
			units=True,
			hierarchical=True,
			out_stream=f,
		)

	# Draw all the connectivity graphs
	viewer = GraphViewer(prob_stand.model)
	for graph_type in ["dataflow", "tree", "cycle"]:
		viewer.write_graph(
			gtype=graph_type,
			display=False,
			show_vars=True,
			outfile=f"figures/teststand_{graph_type}.png",
		)
	#endregion
#endregion

if __name__ == "__main__": main()
