#region Imports
import openmdao.api as om

from openmdao.api import Group

from ..BEARS_Chem import BEARS_Chem

from .comp_injector import InjectorComponent
from .comp_fuel     import FuelComponent
from .comp_chem     import ChemComponent
from .comp_nozzle   import NozzleGeometryComponent, NozzleComponent
#endregion

class HybridEngineGroup(Group):
	"""
	Hybrid engine: injector, fuel grain, combustion chemistry and nozzle

	The chamber pressure couples them: it sets the injector flow and the
	chemistry, which set the chamber pressure through the choked nozzle. A
	Newton solver closes the loop
	"""

	def initialize(self):
		# Chemistry of the propellant combination
		self.options.declare("chem", types=BEARS_Chem)

	def setup(self):
		chem = self.options["chem"]

		#region Subsystems
		self.add_subsystem(
			"Injector",
			InjectorComponent(rho_ox=chem.rho_ox),
			promotes_inputs=[
				("p_tank",  "engine_feed_pressure"),
				("a_inj",   "injector_area"),
				("cd",      "injector_cd"),
			],
			promotes_outputs=[
				("mdot_ox", "engine_mdot_ox"),
				("delta_p", "injector_delta_p"),
			],
		)

		self.add_subsystem(
			"Fuel",
			FuelComponent(rho_fuel=chem.rho_fuel),
			promotes_inputs=[
				("m_prop_i",      "engine_prop_mass_init"),
				("mixture_ratio", "engine_mixture_ratio"),
				("port_diam",     "fuel_port_diam"),
				("n_reg",         "fuel_reg_exponent"),
				("reg_ref",       "fuel_reg_ref"),
				("g_ox_ref",      "fuel_oxy_mass_flux_ref"),
				("eta_reg",       "fuel_eta_reg"),
			],
			promotes_outputs=[
				("length",              "fuel_length"),
				("grain_diam",          "fuel_grain_diam"),
				("r_dot",               "fuel_regression_rate"),
				("mdot_fuel",           "engine_mdot_fuel"),
				("mixture_ratio_init",  "engine_mixture_ratio_init"),
				("mixture_ratio_final", "engine_mixture_ratio_final"),
			],
		)

		# Nozzle geometry: fixed exit and free throat set expansion ratio
		self.add_subsystem(
			"NozzleGeometry",
			NozzleGeometryComponent(),
			promotes_inputs=[
				("d_exit",          "nozzle_exit_diam"),
				("a_throat",        "nozzle_throat_area"),
				("half_angle",      "conical_nozzle_half_angle"),
			],
			promotes_outputs=[
				("a_exit",          "nozzle_exit_area"),
				("expansion_ratio", "nozzle_expansion_ratio"),
				("length",          "nozzle_length"),
			],
		)

		# Combustion chemistry and flame temperature
		self.add_subsystem(
			"Chemistry",
			ChemComponent(chem=chem),
			promotes_inputs=[
				("mixture_ratio",   "engine_mixture_ratio"),
				("expansion_ratio", "nozzle_expansion_ratio"),
				("eta_cstar",       "chem_eta_cstar"),
			],
			promotes_outputs=[
				("isp",             "engine_chem_isp"),
				("t_chamber",       "engine_chamber_temp"),
				("gamma",           "engine_gamma"),
				("molar_mass",      "engine_molar_mass"),
			],
		)

		# Nozzle performance and chamber pressure, from the choked throat
		self.add_subsystem(
			"Nozzle",
			NozzleComponent(),
			promotes_inputs=[
				("mixture_ratio",   "engine_mixture_ratio"),
				("a_throat",        "nozzle_throat_area"),
				("expansion_ratio", "nozzle_expansion_ratio"),
				("half_angle",      "conical_nozzle_half_angle"),
				("eta_friction",    "nozzle_eta_friction"),
				("eta_cstar",       "chem_eta_cstar"),
			],
			promotes_outputs=[
				("mach_exit",       "nozzle_exit_mach"),
				("cstar",           "engine_cstar"),
				("thrust",          "engine_thrust"),
				("isp_delivered",   "engine_isp"),
				("p_chamber",       "engine_chamber_pressure"),
				("p_throat",        "nozzle_throat_pressure"),
				("t_throat",        "nozzle_throat_temp"),
				("p_exit",          "nozzle_exit_pressure"),
				("mdot_prop",       "engine_mdot_prop"),
				("eta_nozzle",      "nozzle_efficiency"),
			],
		)
		#endregion

		#region Connections
		self.connect("engine_chamber_pressure", "Injector.p_chamber")
		self.connect("engine_chamber_pressure", "Chemistry.chamber_pressure")
		self.connect("engine_mdot_ox",          "Fuel.mdot_ox")
		self.connect("engine_mdot_ox",          "Nozzle.mdot_ox")
		self.connect("engine_chamber_temp",     "Nozzle.t_chamber")
		self.connect("engine_gamma",            "Nozzle.gamma")
		self.connect("engine_molar_mass",       "Nozzle.molar_mass")
		self.connect("engine_chem_isp",         "Nozzle.isp")
		#endregion

		#region Solvers
		self.nonlinear_solver = om.NewtonSolver(solve_subsystems=False)
		self.nonlinear_solver.options["maxiter"] = 30
		self.nonlinear_solver.options["rtol"]    = 1e-6
		self.nonlinear_solver.options["atol"]    = 1e-6
		self.nonlinear_solver.options["iprint"]  = 0
		self.nonlinear_solver.linesearch = om.ArmijoGoldsteinLS()

		self.linear_solver = om.DirectSolver()
		#endregion
