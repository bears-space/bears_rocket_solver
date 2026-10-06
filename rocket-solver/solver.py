#!.env/bin/python
"""
The rocket optimization script using OpenMDAO for the framework

@author:  Andrii
@license: GPL-3.0-or-later
"""

#region Imports
import os
import numpy        as np
import openmdao.api as om
import rocketcea.cea_obj as cea_obj

from scipy.integrate   import solve_ivp
from scipy.interpolate import interp1d
from scipy.constants   import g
from openmdao.visualization.graph_viewer import GraphViewer

import openmdao.utils.variable_table as vt
import openmdao.core.system          as sys_mod

from modules.Config          import load_configs, load_reactants
from modules.BEARS_Atmo      import BEARS_Atm
from modules.BEARS_Chem      import Thermochemistry
from modules.BEARS_Materials import Layer, LayeredWall, AL_6061_T6, CFRP_T700
from modules.BEARS_Rocket    import TestStandProblem, RocketLaunchProblem
#endregion

#region Helpers
def patch_variable_table():
	"""
	Dirty hack to prevent OpenMDAO from taking the Euclidean norm of array
	variables for the variable printout, since that makes no sense for this
	setup
	"""

	orig_write = vt.write_var_table

	def patched_write(
		pathname,
		var_list,
		var_type,
		var_dict,
		hierarchical=True,
		print_arrays=False,
		out_stream=None,
	):
		patched = {}
		for k, meta in var_dict.items():
			meta_copy = dict(meta)
			val = meta_copy.get("val")
			if isinstance(val, np.ndarray) and val.size > 1:
				meta_copy["val"] = np.array2string(
					val, precision=6, separator=", "
				)
			patched[k] = meta_copy

		return orig_write(
			pathname, var_list, var_type, patched,
			hierarchical=hierarchical, print_arrays=print_arrays,
			out_stream=out_stream,
		)

	vt.write_var_table      = patched_write
	sys_mod.write_var_table = patched_write
#endregion

#region Main
def main():
	patch_variable_table()

	#region Working directories
	work_dir = os.path.abspath("work")
	os.makedirs(work_dir, exist_ok=True)
	cea_obj.ROCKETCEA_DATA_DIR = os.path.join(work_dir, "RocketCEA")
	#endregion

	#region Inputs
	cfg_rocket = load_configs("inputs/rocket.default.toml")
	cfg_reac   = load_reactants("inputs/reactants.toml")

	atm = BEARS_Atm("isacalc")

	chem = Thermochemistry.from_config(cfg_reac)

	copv_ox = LayeredWall(
		Layer(material=AL_6061_T6, thickness=0.001),
		Layer(material=CFRP_T700, helical_angle_deg=20.0, efficiency=0.85),
		# ^ Dynamically sized for remaining pressure
	)
	#endregion

	#region Rocket optimization
	prob_rocket = RocketLaunchProblem(
		atm=atm,
		chem=chem,
		payload_mass=cfg_rocket.cfg_global.payload_mass_kg,
		target_apogee=cfg_rocket.cfg_global.target_altitude_m,
		ox_wall_material=copv_ox,
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
	prob_stand = TestStandProblem(chem=chem, reports=False)

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
