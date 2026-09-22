# region Imports
import openmdao.api as om

from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_tank     import TankComponent
from .comp_injector import InjectorComponent
from .comp_fuel     import FuelComponent
from .comp_chem     import ChemComponent
from .comp_nozzle   import NozzleComponent
# endregion

class PropulsionGroup(Group):

	def initialize(self):
		self.options.declare("cea",      types=CEA_Obj)
		self.options.declare("rho_ox",   default=1200.0, types=float)
		self.options.declare("rho_fuel", default=900.0,  types=float)

	def setup(self):
		cea      = self.options["cea"]
		rho_ox   = self.options["rho_ox"]
		rho_fuel = self.options["rho_fuel"]

		#region Subsystems
		self.add_subsystem(
			"Tank",
			TankComponent(rho_ox=rho_ox),
			promotes_inputs=[
				("m_prop_i",      "prop_prop_mass_init"),
				("mixture_ratio", "prop_mixture_ratio"),
				("diam_out",      "tank_diam"),
				("ullage_frac",   "tank_ullage_frac"),
				("sigma_y",       "tank_yield_factor"),
				("safety_factor", "tank_safety_factor"),
				("rho_wall",      "tank_wall_density"),
				("p_tank_max",    "tank_pressure"),
			],
			promotes_outputs=[
				("m_tank_dry", "tank_dry_mass"),
				("l_tank",     "tank_length"),
				("v_internal", "tank_volume"),
				("t_wall",     "tank_wall_thickness"),
			],
		)

		self.add_subsystem(
			"Injector",
			InjectorComponent(rho_ox=rho_ox),
			promotes_inputs=[
				("p_tank", "tank_pressure"),
				("a_inj",  "injector_area"),
				("cd",     "injector_cd"),
			],
		)

		self.add_subsystem(
			"Fuel",
			FuelComponent(rho_fuel=rho_fuel),
			promotes_inputs=[
				("m_prop_i",      "prop_prop_mass_init"),
				("mixture_ratio", "prop_mixture_ratio"),
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
			],
		)

		self.add_subsystem(
			"Chemistry",
			ChemComponent(cea=cea),
			promotes_inputs=[
				("mixture_ratio",   "prop_mixture_ratio"),
				("expansion_ratio", "nozzle_expansion_ratio"),
			],
			promotes_outputs=[
				("isp",             "chem_isp"),
			],
		)

		self.add_subsystem(
			"Nozzle",
			NozzleComponent(),
			promotes_inputs=[
				("mixture_ratio",   "prop_mixture_ratio"),
				("a_throat",        "nozzle_throat_area"),
				("expansion_ratio", "nozzle_expansion_ratio"),
				("length",          "nozzle_length"),
				("eta_friction",    "nozzle_eta_friction"),
			],
			promotes_outputs=[
				("thrust",          "nozzle_thrust"),
				("eta_nozzle",      "nozzle_efficiency"),
				("p_chamber",       "prop_chamber_pressure"),
				("exit_half_angle", "nozzle_exit_half_angle"),
			],
		)
		#endregion

		#region Connections
		self.connect("prop_chamber_pressure", "Injector.p_chamber")
		self.connect("prop_chamber_pressure", "Chemistry.chamber_pressure")
		self.connect("Injector.mdot_ox", "Fuel.mdot_ox")
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

