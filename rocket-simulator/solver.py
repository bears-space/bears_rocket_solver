#!/usr/bin/env python
"""
@author: Andrii
@date: 28.07.2026
"""

#region Imports
import json
import cea
import numpy        as np
import openmdao.api as om

from dataclasses import dataclass, replace
#endregion

#region Main
def main():
	prob = om.Problem()

	prob.model.add_subsystem(
		"paraboloid",
		om.ExecComp("f = (x-3)**2 + x*y + (y+4)**2 - 3")
	)

	prob.driver = om.ScipyOptimizeDriver()
	prob.driver.options["optimizer"] = "SLSQP"

	prob.model.add_design_var("paraboloid.x", lower=-50, upper=50)
	prob.model.add_design_var("paraboloid.y", lower=-50, upper=50)
	prob.model.add_objective("paraboloid.f")

	prob.setup()

	prob.set_val("paraboloid.x",  2.0)
	prob.set_val("paraboloid.y", -4.0)

	prob.run_driver()

	print(prob.get_val("paraboloid.f"))
	print(prob.get_val("paraboloid.x"))
	print(prob.get_val("paraboloid.y"))
#endregion

if __name__=="__main__": main()
