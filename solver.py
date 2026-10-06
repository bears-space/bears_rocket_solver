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
	Thermochemistry.set_work_dir(os.path.join(work_dir, "RocketCEA"))
	#endregion

	#region Inputs
	cfg_rocket = load_configs("inputs/rocket.toml")
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
	res_rocket = prob_rocket.run()

	m_prop_opt   = res_rocket['m_prop_kg']
	mr_opt       = res_rocket['mr']
	a_inj_opt    = res_rocket['a_inj_mm2']
	a_throat_opt = res_rocket['a_throat_cm2']

	prob_rocket.report(res_rocket)
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

	res_stand = prob_stand.run()

	prob_stand.report(res_stand)
	#endregion
#endregion

if __name__ == "__main__": main()
