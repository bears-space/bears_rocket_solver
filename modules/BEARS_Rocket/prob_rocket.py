#region Imports
import os
import openmdao.api as om

from scipy.constants import g
from openmdao.api    import Problem
from openmdao.visualization.graph_viewer import GraphViewer

from ..Config     import OptimizationSeedConfig, EfficienciesConfig
from ..BEARS_Chem import BEARS_Chem
from ..BEARS_Atmo import BEARS_Atm

from .group_rocket import RocketGroup
from .graph_style  import has_graphviz, style_graph

from .checks  import CheckFn, DEFAULT_ROCKET_CHECKS, run_checks
#endregion

class RocketLaunchProblem(Problem):

	def __init__(
		self,
		atm                 : BEARS_Atm,
		chem                : BEARS_Chem,
		payload_mass        : float = 1.0,
		nonprop_mass        : float = 5.0,
		target_apogee       : float = 3100.0,
		ox_wall_material    = None,
		press_wall_material = None,
		seed_optim          : OptimizationSeedConfig | None = None,
		cfg_efficiencies    : EfficienciesConfig | None = None,
		checks              : tuple[CheckFn, ...] = DEFAULT_ROCKET_CHECKS,
		**kwargs,
	):
		super().__init__(**kwargs)

		self.model = RocketGroup(
			atm                 = atm,
			chem                = chem,
			ox_wall_material    = ox_wall_material,
			press_wall_material = press_wall_material,
		)

		self.driver = om.ScipyOptimizeDriver()
		self.driver.options["optimizer"] = "SLSQP"

		self.checks = checks

		# - Design variables

		# Store payload mass and target apogee as an instance attribute
		self.payload_mass     = payload_mass
		self.nonprop_mass     = nonprop_mass
		self.target_apogee    = target_apogee
		self.seed_optim       = seed_optim
		self.cfg_efficiencies = cfg_efficiencies

		eta_t = 0.92 if cfg_efficiencies is None else cfg_efficiencies.trajectory
		eff_apogee = target_apogee / eta_t

		self.model.add_design_var(
			"OptimizationVars.o_propellant_mass",
			lower = 1.0,
			upper = 10.0,
			ref   = 5.0,
		)

		self.model.add_design_var(
			"OptimizationVars.o_mixture_ratio",
			lower = 4.0,
			upper = 10.0,
			ref   = 6.0,
		)

		self.model.add_design_var(
			"OptimizationVars.o_injector_area",
			lower = 0.5e-5,
			upper = 3.0e-4,
			ref   = 1.5e-5,
		)

		self.model.add_design_var(
			"OptimizationVars.o_nozzle_throat_area",
			lower = 1.0e-4,
			upper = 6.0e-4,
			ref   = 2.0e-4,
		)

		# - Constraints
		self.model.add_constraint(
			"apogee",
			lower = eff_apogee,
			ref   = eff_apogee,
		)

		self.model.add_constraint(
			"burn_time",
			lower = 5.0,
			upper = 15.0,
			ref   = 6.0,
		)

		self.model.add_constraint(
			"Propulsion.prop_thrust",
			upper = 1200.0,
			ref   = 1000.0,
		)

		# Injector pressure drop safety margin
		self.model.add_constraint(
			"Propulsion.injector_delta_p",
			lower = 20.0,
			ref   = 20.0,
			units = "bar",
		)

		# - Objective
		self.model.add_objective(
			"OptimizationVars.o_propellant_mass",
			ref = 10.0,
		)

	def setup(self, **kwargs):
		super().setup(**kwargs)

		# Vehicle parameters
		self.set_val("DesignVars.g_payload_mass", self.payload_mass, units="kg")
		self.set_val("DesignVars.g_nonprop_mass", self.nonprop_mass, units="kg")

		self.set_val("DesignVars.g_diameter",                 0.12)
		self.set_val("DesignVars.press_diam",                 0.12)
		self.set_val("DesignVars.tank_pressure",              70)
		self.set_val("DesignVars.tank_diam",                  0.12)
		self.set_val("DesignVars.injector_cd",                0.7)
		self.set_val("DesignVars.fuel_port_diam",             0.05)
		self.set_val("DesignVars.fuel_reg_exponent",          0.5)
		self.set_val("DesignVars.fuel_reg_ref",               1.0e-4)
		self.set_val("DesignVars.nozzle_expansion_ratio",     5.0)

		ef = self.cfg_efficiencies
		eta_c = 0.88 if ef is None else ef.combustion
		eta_t = 0.92 if ef is None else ef.trajectory
		eta_p = 0.92 if ef is None else ef.propellant_utilization
		eta_r = 0.60 if ef is None else ef.regression_correction
		eta_n = 0.95 if ef is None else ef.nozzle_friction

		self.set_val("DesignVars.eta_combustion",             eta_c)
		self.set_val("DesignVars.eta_trajectory",             eta_t)
		self.set_val("DesignVars.eta_propellant",             eta_p)
		self.set_val("DesignVars.eta_regression",             eta_r)
		self.set_val("DesignVars.nozzle_eta_friction",        eta_n)

		so = self.seed_optim
		m_init  = 5.0    if so is None else so.propellant_mass_kg
		mr_init = 7.0    if so is None else so.mixture_ratio
		ai_init = 1.5e-5 if so is None else so.injector_area_m2
		at_init = 2.0e-4 if so is None else so.nozzle_throat_area_m2

		# Starting point for optimization
		self.set_val("OptimizationVars.o_propellant_mass",    m_init)
		self.set_val("OptimizationVars.o_mixture_ratio",      mr_init)
		self.set_val("OptimizationVars.o_injector_area",      ai_init)
		self.set_val("OptimizationVars.o_nozzle_throat_area", at_init)

		return self

	def run(self):
		self.run_driver()
		return self

	#region Verification
	def verify(self, raise_on_error : bool = True):
		"""Validate post-run physical quantities and optimization results"""
		return run_checks(self, self.checks, raise_on_error=raise_on_error)
	#endregion

	#region Outputs
	def print_summary(self):

		FMT = "8.3f"

		self.verify()

		m_prop = self.get_val("OptimizationVars.o_propellant_mass",    units="kg")[0]
		m_ld   = self.get_val("Mass.prop_loaded_mass",                 units="kg")[0]
		a_inj  = self.get_val("OptimizationVars.o_injector_area",      units="mm**2")[0]
		a_thr  = self.get_val("OptimizationVars.o_nozzle_throat_area", units="cm**2")[0]
		mr     = self.get_val("OptimizationVars.o_mixture_ratio")[0]
		ap     = self.get_val("apogee",                                units="m")[0]
		t_burn = self.get_val("burn_time",                             units="s")[0]
		thr    = self.get_val("Propulsion.prop_thrust",                units="N")[0]
		isp    = self.get_val("Propulsion.prop_isp",                   units="s")[0]
		pch    = self.get_val("Propulsion.prop_chamber_pressure",      units="bar")[0]
		tch    = self.get_val("Propulsion.prop_chamber_temp",          units="K")[0]
		dp     = self.get_val("Propulsion.injector_delta_p",           units="bar")[0]
		mdry   = self.get_val("Mass.dry_mass",                         units="kg")[0]
		mpr    = self.get_val("Mass.pressurant_mass",                  units="kg")[0]
		mi     = self.get_val("Mass.initial_mass",                     units="kg")[0]
		twr    = thr / (mi * g)

		print("Optimized rocket parameters:")
		print("")
		print(f"Burned (optimized) m_prop:\t{m_prop:{FMT}} kg")
		print(f"Loaded m_prop:            \t{m_ld:{FMT}} kg")
		print(f"Optimized A_inj:          \t{a_inj:{FMT}} mm²")
		print(f"Optimized A_throat:       \t{a_thr:{FMT}} cm²")
		print(f"Optimized MR:             \t{mr:{FMT}}")
		print("")
		print(f"Apogee:                   \t{ap:{FMT}} m")
		print(f"Burn time:                \t{t_burn:{FMT}} s")
		print(f"Liftoff thrust:           \t{thr:{FMT}} N")
		print(f"Liftoff Isp:              \t{isp:{FMT}} s")
		print(f"Chamber pressure:         \t{pch:{FMT}} bar")
		print(f"Chamber flame temp:       \t{tch:{FMT}} K")
		print(f"Injector ΔP:              \t{dp:{FMT}} bar")
		print("")
		print(f"Dry mass:                 \t{mdry:{FMT}} kg")
		print(f"Pressurant mass:          \t{mpr:{FMT}} kg")
		print(f"Total mass at liftoff:    \t{mi:{FMT}} kg")
		print(f"TWR at launch:            \t{twr:{FMT}}")

	def print_parameters(self, path: str = "outputs/rocket.txt"):
		"""Dump all computed variables to an output file"""

		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, mode="wt") as f:
			self.model.list_outputs(
				val          = True,
				units        = True,
				hierarchical = True,
				out_stream   = f,
			)

	def print_graphs(self, out_dir: str = "figures", prefix: str = "rocket"):
		"""Draw all the connectivity graphs, provided Graphviz is installed"""

		if not has_graphviz():
			print(f"Graphviz ('dot') not found, skipping {prefix} graphs")
			return

		os.makedirs(out_dir, exist_ok=True)
		viewer = GraphViewer(self.model)
		for gtype in ["dataflow", "tree", "cycle"]:
			png_path = os.path.join(out_dir, f"{prefix}_{gtype}.png")
			svg_path = os.path.join(out_dir, f"{prefix}_{gtype}.svg")
			dot = viewer.write_graph(
				gtype     = gtype,
				display   = False,
				show_vars = True,
				#exclude   = ("_auto_ivc",),
				outfile   = png_path,
			)
			if dot is not None:
				match gtype:
					case "dataflow":
						# "spline" | "ortho" | "curved" | "line" | "polyline"
						splines = "spline" 
					case "tree":
						splines = "spline"
					case "cycle":
						splines = "spline"
				dot = style_graph(dot, splines=splines, concentrate=True)
				dot.write_png(png_path)

	def report(
		self,
		out_txt : str  = "outputs/rocket.txt",
		graphs  : bool = True,
	):
		"""Print results and generate output artifacts"""

		self.print_summary()
		self.print_parameters(out_txt)
		if graphs:
			self.print_graphs()
	#endregion
