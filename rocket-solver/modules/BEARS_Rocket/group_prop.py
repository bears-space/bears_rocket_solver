# region Imports
import openmdao.api as om

from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_tank     import TankComponent
from .comp_injector import InjectorComponent
from .comp_chem     import ChemComponent
from .comp_nozzle   import NozzleComponent
# endregion

class PropulsionGroup(Group):

	def initialize(self):
		self.options.declare("cea", types=CEA_Obj)

	def setup(self):
		cea = self.options["cea"]

		#region Subsystems
		self.add_subsystem(
			"Tank",
			TankComponent(),
			promotes_inputs=[
				"diam_out", "m_prop_i", "mixture_ratio",
				("p_tank_max", "p_tank"),
			],
			promotes_outputs=["m_tank_dry"],
		)

		# Between tank and injector we have a ~30bar pressure loss
		# -> "Plumbing component"
		# TODO: elaborate the plumbing with the rest of the team

		self.add_subsystem(
			"Injector",
			InjectorComponent(),
			promotes_inputs=["p_tank", "rho_ox"],
		)

		self.add_subsystem(
			"Chemistry",
			ChemComponent(cea=cea),
			promotes_inputs=["mixture_ratio", "expansion_ratio"],
			promotes_outputs=["isp"],
		)

		self.add_subsystem(
			"Nozzle",
			NozzleComponent(),
			promotes_inputs=["mixture_ratio", "isp"],
			promotes_outputs=["thrust"],
		)
		#endregion

		#region Connections
		self.connect("Nozzle.p_chamber", "Injector.p_chamber")
		self.connect("Nozzle.p_chamber", "Chemistry.chamber_pressure")
		self.connect("Injector.mdot_ox", "Nozzle.mdot_ox")
		self.connect("Chemistry.cstar",  "Nozzle.cstar")
		#endregion

		#region Solvers
		self.nonlinear_solver = om.NewtonSolver(solve_subsystems=False)
		self.nonlinear_solver.options["maxiter"] = 25
		self.nonlinear_solver.options["rtol"] = 1e-6
		self.nonlinear_solver.options["iprint"] = 0
		self.nonlinear_solver.linesearch = om.ArmijoGoldsteinLS()

		self.linear_solver = om.DirectSolver()
		#endregion

