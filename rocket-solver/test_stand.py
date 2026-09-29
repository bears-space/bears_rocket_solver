#!/usr/bin/env python

#region Imports
import json
import os
import openmdao.api      as om
import rocketcea.cea_obj as cea_obj

from rocketcea.cea_obj                    import CEA_Obj
from openmdao.visualization.graph_viewer  import GraphViewer

from modules.BEARS_Chem                   import parse_reactants, parse_densities
from modules.BEARS_Rocket.group_teststand import TestStandGroup
#endregion

#region Main
def main():

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

	cea = CEA_Obj(oxName=oname, fuelName=fname)

	# Problem setup
	prob = om.Problem(reports=True, work_dir=work_dir)
	prob.model = TestStandGroup(cea=cea, rho_ox=rho_ox, rho_fuel=rho_fuel)
	prob.setup()

	# Static test conditions
	# - Boundary conditions
	PT1_N2O_supply = 65.0   # bar
	TC1_N2O_supply = 288.15 # K (15 °C)
	PT4_N2_supply  = 200.0  # bar
	TC4_run_dome   = 285.15 # K
	TC2_run_liquid = 275.15 # K

	# - Run rank setting (PT2)
	prob.set_val("run_tank_pressure_PT2", 60.0, units="bar")
	prob.set_val("run_tank_fluid_mass",   15.0, units="kg")
	prob.set_val("run_tank_diam",         0.15, units="m")
	prob.set_val("run_tank_ullage_frac",  0.08)

	# - Motor hardware
	prob.set_val("injector_area",          1.5e-5, units="m**2")
	prob.set_val("injector_cd",            0.7)
	prob.set_val("fuel_port_diam",         0.05,   units="m")
	prob.set_val("fuel_reg_exponent",      0.50)
	prob.set_val("fuel_reg_ref",           1.0e-4, units="m/s")
	prob.set_val("nozzle_throat_area",     2.0e-4, units="m**2")
	prob.set_val("nozzle_expansion_ratio", 15.0)
	prob.set_val("nozzle_length",          0.15,   units="m")

	# - Propellant charge
	prob.set_val("test_prop_mass_init",    8.0,    units="kg")
	prob.set_val("test_mixture_ratio",     6.618)

	prob.run_model()

	# Sensor values
	PT2_val = prob.get_val("run_tank_pressure_PT2",     units="bar")[0]
	PT3_val = prob.get_val("test_chamber_pressure_PT3", units="bar")[0]
	TC3_val = prob.get_val("test_chamber_temp_TC3",     units="K")[0]
	thrust  = prob.get_val("test_thrust",               units="N")[0]
	isp     = prob.get_val("chem_isp",                  units="s")[0]

	print(f"PT1 (N2O supply pressure):       {PT1_N2O_supply:6.2f} bar")
	print(f"TC1 (N2O supply temperature):    {TC1_N2O_supply:6.2f} K")
	print(f"PT4 (N2 pressurant temperature): {PT4_N2_supply:6.2f} bar")
	print("")
	print(f"PT2 (run tank feed temperature): {PT2_val:6.2f} bar")
	print(f"TC2 (run tank liquid temp):      {TC2_run_liquid:6.2f} K")
	print(f"TC4 (run tank dome temp):        {TC4_run_dome:6.2f} K")
	print("")
	print(f"PT3 (chamber pressure):          {PT3_val:6.2f} bar")
	print(f"TC3 (chamber flame temp):        {TC3_val:6.2f} K")
	print(f"Delta-P injector (PT2 - PT3):    {PT2_val - PT3_val:6.2f} bar")
	print("")
	print(f"Thrust:                          {thrust:6.2f} N")
	print(f"Isp:                             {isp:6.2f} s")

	with open("outputs/teststand.txt", mode="wt") as f:
		prob.model.list_outputs(
			val=True,
			units=True,
			hierarchical=True,
			out_stream=f,
		)

	viewer = GraphViewer(prob.model)
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
