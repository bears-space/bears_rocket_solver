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

class TestStandGroup(Group):

	def initialize(self):
		self.options.declare("cea",                     types=CEA_Obj)
		self.options.declare("rho_ox",   default=750.0, types=float)
		self.options.declare("rho_fuel", default=900.0, types=float)

	def setup(self):
		cea      = self.options["cea"]
		rho_ox   = self.options["rho_ox"]
		rho_fuel = self.options["rho_fuel"]

		self.set_input_defaults("run_tank_pressure_PT2", val=60e5,   units="Pa")
		self.set_input_defaults("run_tank_density",      val=rho_ox, units="kg/m**3")
		self.set_input_defaults("run_tank_fluid_mass",   val=10.0,   units="kg")

		#region Subsystems
		# Run tank (PT2)
		self.add_subsystem(
			"RunTank",
			TankComponent(),
			promotes_inputs=[
				("m_fluid",     "run_tank_fluid_mass"),
				("rho_fluid",   "run_tank_density"),
				("p_tank_max",  "run_tank_pressure_PT2"),
				("diam_out",    "run_tank_diam"),
				("ullage_frac", "run_tank_ullage_frac"),
				("rho_wall",    "run_tank_wall_density"),
				("sigma_y",     "run_tank_yield_factor"),
			],
			promotes_outputs=[
				("v_internal",  "run_tank_volume"),
				("l_tank",      "run_tank_length"),
				("m_tank_dry",  "run_tank_dry_mass"),
			],
		)

		# Injector fed from run tank (PT2)
		self.add_subsystem(
			"Injector",
			InjectorComponent(rho_ox=rho_ox),
			promotes_inputs=[
				("p_tank", "run_tank_pressure_PT2"),
				("a_inj",  "injector_area"),
				("cd",     "injector_cd"),
			],
		)

		self.add_subsystem(
			"Fuel",
			FuelComponent(rho_fuel=rho_fuel),
			promotes_inputs=[
				("m_prop_i",      "test_prop_mass_init"),
				("mixture_ratio", "test_mixture_ratio"),
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

		# Combustion chemistry & flame temperature (TC3)
		self.add_subsystem(
			"Chemistry",
			ChemComponent(cea=cea),
			promotes_inputs=[
				("mixture_ratio",   "test_mixture_ratio"),
				("expansion_ratio", "nozzle_expansion_ratio"),
			],
			promotes_outputs=[
				("isp",             "chem_isp"),
				("t_chamber",       "test_chamber_temp_TC3"),
			],
		)

		# Nozzle performance & chamber pressure (PT3)
		self.add_subsystem(
			"Nozzle",
			NozzleComponent(),
			promotes_inputs=[
				("mixture_ratio",   "test_mixture_ratio"),
				("a_throat",        "nozzle_throat_area"),
				("expansion_ratio", "nozzle_expansion_ratio"),
				("length",          "nozzle_length"),
				("eta_friction",    "nozzle_eta_friction"),
			],
			promotes_outputs=[
				("thrust",          "test_thrust"),
				("eta_nozzle",      "nozzle_efficiency"),
				("exit_half_angle", "nozzle_exit_half_angle"),
				("p_chamber",       "test_chamber_pressure_PT3"),
			],
		)
		#endregion

		#region Connections
		self.connect("test_chamber_pressure_PT3", "Injector.p_chamber")
		self.connect("test_chamber_pressure_PT3", "Chemistry.chamber_pressure")
		self.connect("Injector.mdot_ox", "Fuel.mdot_ox")
		self.connect("Injector.mdot_ox", "Nozzle.mdot_ox")
		self.connect("Chemistry.cstar",  "Nozzle.cstar")
		self.connect("chem_isp",         "Nozzle.isp")
		#endregion

		#region Solvers
		self.nonlinear_solver = om.NewtonSolver(solve_subsystems=False)
		self.nonlinear_solver.options["maxiter"] = 30
		self.nonlinear_solver.options["rtol"]    = 1e-6
		self.nonlinear_solver.options["iprint"]  = 0
		self.nonlinear_solver.linesearch = om.ArmijoGoldsteinLS()

		self.linear_solver = om.DirectSolver()
		#endregion
