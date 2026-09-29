# region Imports
import openmdao.api as om

from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_injector import InjectorComponent
from .comp_fuel     import FuelComponent
from .comp_chem     import ChemComponent
from .comp_nozzle   import NozzleComponent
# endregion

class HybridEngineGroup(Group):

	def initialize(self):
		self.options.declare("cea",                     types=CEA_Obj)
		self.options.declare("rho_ox",   default=750.0, types=float)
		self.options.declare("rho_fuel", default=750.0, types=float)

	def setup(self):
		cea      = self.options["cea"]
		rho_ox   = self.options["rho_ox"]
		rho_fuel = self.options["rho_fuel"]

		self.set_input_defaults("engine_feed_pressure", val=60e5, units="Pa")

		#region Subsystems
		self.add_subsystem(
			"Injector",
			InjectorComponent(rho_ox=rho_ox),
			promotes_inputs=[
				("p_tank",  "engine_feed_pressure"),
				("a_inj",   "injector_area"),
				("cd",      "injector_cd"),
			],
			promotes_outputs=[
				("mdot_ox", "engine_mdot_ox"),
			],
		)

		self.add_subsystem(
			"Fuel",
			FuelComponent(rho_fuel=rho_fuel),
			promotes_inputs=[
				("m_prop_i",      "engine_prop_mass_init"),
				("mixture_ratio", "engine_mixture_ratio"),
				("port_diam",     "fuel_port_diam"),
				("n_reg",         "fuel_reg_exponent"),
				("reg_ref",       "fuel_reg_ref"),
				("g0_ref",        "fuel_oxy_mass_flux_ref"),
			],
			promotes_outputs=[
				("length",     "fuel_length"),
				("grain_diam", "fuel_grain_diam"),
				("r_dot",      "fuel_regression_rate"),
				("m_fuel",     "fuel_mass"),
				("mdot_fuel",  "engine_mdot_fuel"),
			],
		)

		# Combustion chemistry & flame temperature (TC3)
		self.add_subsystem(
			"Chemistry",
			ChemComponent(cea=cea),
			promotes_inputs=[
				("mixture_ratio",   "engine_mixture_ratio"),
				("expansion_ratio", "nozzle_expansion_ratio"),
			],
			promotes_outputs=[
				("isp",             "engine_isp"),
				("cstar",           "engine_cstar"),
			],
		)

		# Nozzle performance & chamber pressure (PT3)
		self.add_subsystem(
			"Nozzle",
			NozzleComponent(),
			promotes_inputs=[
				("mixture_ratio",   "engine_mixture_ratio"),
				("a_throat",        "nozzle_throat_area"),
				("expansion_ratio", "nozzle_expansion_ratio"),
				("length",          "nozzle_length"),
				("eta_friction",    "nozzle_eta_friction"),
			],
			promotes_outputs=[
				("thrust",          "engine_thrust"),
				("p_chamber",       "engine_chamber_pressure"),
				("mdot_prop",       "engine_mdot_prop"),
				("eta_nozzle",      "nozzle_efficiency"),
				("exit_half_angle", "nozzle_exit_half_angle"),
			],
		)
		#endregion

		#region Connections
		self.connect("engine_chamber_pressure", "Injector.p_chamber")
		self.connect("engine_chamber_pressure", "Chemistry.chamber_pressure")
		self.connect("engine_mdot_ox",          "Fuel.mdot_ox")
		self.connect("engine_mdot_ox",          "Nozzle.mdot_ox")
		self.connect("engine_cstar",            "Nozzle.cstar")
		self.connect("engine_isp",              "Nozzle.isp")
		#endregion

		#region Solvers
		self.nonlinear_solver = om.NewtonSolver(solve_subsystems=False)
		self.nonlinear_solver.options["maxiter"] = 30
		self.nonlinear_solver.options["rtol"]    = 1e-6
		self.nonlinear_solver.options["iprint"]  = 0
		self.nonlinear_solver.linesearch = om.ArmijoGoldsteinLS()

		self.linear_solver = om.DirectSolver()
		#endregion
