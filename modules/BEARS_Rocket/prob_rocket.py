#region Imports
import os
import openmdao.api as om

from scipy.constants import g
from openmdao.api    import Problem
from openmdao.visualization.graph_viewer import GraphViewer

from ..BEARS_Chem import BEARS_Chem
from ..BEARS_Atmo import BEARS_Atm

from .group_rocket import RocketGroup
#endregion

class RocketLaunchProblem(Problem):

	def __init__(
		self,
		atm                 : BEARS_Atm,
		chem                : BEARS_Chem,
		payload_mass        : float = 1.0,
		target_apogee       : float = 3100.0,
		ox_wall_material    = None,
		press_wall_material = None,
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

		# - Design variables

		# Store payload mass and target apogee as an instance attribute
		self.payload_mass  = payload_mass
		self.target_apogee = target_apogee

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
			upper = 3.0e-5,
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
			lower = target_apogee,
			ref   = target_apogee,
		)

		self.model.add_constraint(
			"burn_time",
			lower = 2.0,
			upper = 8.0,
			ref   = 5.0,
		)

		self.model.add_constraint(
			"Propulsion.prop_thrust",
			upper = 1800.0,
			ref   = 1500.0,
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

		self.set_val("DesignVars.g_diameter",                 0.12)
		self.set_val("DesignVars.press_diam",                 0.12)
		self.set_val("DesignVars.tank_pressure",              70)
		self.set_val("DesignVars.tank_diam",                  0.12)
		self.set_val("DesignVars.injector_cd",                0.7)
		self.set_val("DesignVars.fuel_port_diam",             0.05)
		self.set_val("DesignVars.fuel_reg_exponent",          0.5)
		self.set_val("DesignVars.fuel_reg_ref",               1.0e-4)
		self.set_val("DesignVars.nozzle_expansion_ratio",     40.0)

		# Starting point for optimization
		self.set_val("OptimizationVars.o_propellant_mass",    5.0)
		self.set_val("OptimizationVars.o_mixture_ratio",      6.0)
		self.set_val("OptimizationVars.o_injector_area",      1.5e-5)
		self.set_val("OptimizationVars.o_nozzle_throat_area", 2.0e-4)

		return self

	def run(self):

		self.run_driver()

		# TWR at launch
		thr = self.get_val("Propulsion.prop_thrust")[0]
		mi  = self.get_val("Mass.initial_mass")[0]
		twr = thr / (mi * g)

		# Calculated mass
		mdry  = self.get_val("Mass.dry_mass")[0]
		mprop = self.get_val("OptimizationVars.o_propellant_mass")[0]
		mpr   = self.get_val("Mass.pressurant_mass")[0]

		mcalc = mdry + mprop + mpr

		# Apogee error
		ap = self.get_val("apogee")[0]
		ap_err = abs(ap - self.target_apogee)

		# Random values that were too long and didn't look pretty
		# in the dict return statement
		ainj = self.get_val(
			"OptimizationVars.o_injector_area",
			units="mm**2",
		)[0]

		athr = self.get_val(
			"OptimizationVars.o_nozzle_throat_area",
			units="cm**2",
		)[0]

		pch = self.get_val(
			"Propulsion.prop_chamber_pressure",
			units="bar",
		)[0]

		dp = self.get_val(
			"Propulsion.injector_delta_p",
			units="bar"
		)[0]

		return {
			"m_prop_kg"      : mprop,
			"mr"             : self.get_val("OptimizationVars.o_mixture_ratio")[0],
			"a_inj_mm2"      : ainj,
			"a_throat_cm2"   : athr,
			"apogee_m"       : ap,
			"apogee_error_m" : ap_err,
			"burn_time_s"    : self.get_val("burn_time")[0],
			"thrust_N"       : thr,
			"isp_s"          : self.get_val("Propulsion.prop_isp")[0],
			"m_dry_kg"       : mdry,
			"m_initial_kg"   : mi,
			"m_press_kg"     : mpr,
			"p_chamber_bar"  : pch,
			"delta_p_bar"    : dp,
			"m_calc_kg"      : mcalc,
			"twr_launch"     : twr,
		}

	#region Verification
	def verify(
		self,
		res            : dict,
		raise_on_error : bool = True,
	) -> tuple[str, ...]:
		"""Validate post-run physical quantities and optimization results"""
		errors   : list[str] = []
		warnings : list[str] = []

		# 1. Forward fluid flow through injector
		if res["delta_p_bar"] <= 0.0:
			errors.append(f"Injector ΔP non-positive ({res['delta_p_bar']:.3f} bar)")
		elif res["delta_p_bar"] / res["p_chamber_bar"] < 0.15:
			ratio = res["delta_p_bar"] / res["p_chamber_bar"]
			warnings.append(f"Injector ΔP ratio is low ({ratio:.1%})")

		# 2. Liftoff thrust-to-weight ratio
		if res["twr_launch"] < 1.0:
			errors.append(f"Liftoff TWR below 1.0 ({res['twr_launch']:.2f})")
		elif res["twr_launch"] < 1.3:
			warnings.append(f"Liftoff TWR is low ({res['twr_launch']:.2f})")

		# 3. Mass balance
		if abs(res["m_initial_kg"] - res["m_calc_kg"]) > 1e-3:
			errors.append(
				f"Mass balance mismatch: "
				f"{res['m_initial_kg']:.3f} kg != {res['m_calc_kg']:.3f} kg"
			)

		# 4. Apogee target error
		if res["apogee_error_m"] > 20.0:
			warnings.append(f"Apogee target error is {res['apogee_error_m']:.2f} m")

		# 5. Realistic combusion envelope
		if not (150.0 <= res["isp_s"] <= 350.0):
			warnings.append(f"Isp ({res['isp_s']:.1f} s) outside range [150, 350]")

		if raise_on_error and errors:
			msg = "\n  - ".join(errors)
			raise ValueError(f"Post-run verification failed:\n  - {msg}")

		for w in warnings:
			print(f"Warning {w}")

		return tuple(errors + warnings)
	#endregion

	#region Outputs
	def print_summary(self, res: dict):

		FMT = "8.3f"

		self.verify(res)

		print("Optimized rocket parameters:")
		print("")
		print(f"Optimized m_prop:     \t{res['m_prop_kg']:{FMT}} kg")
		print(f"Optimized A_inj:      \t{res['a_inj_mm2']:{FMT}} mm²")
		print(f"Optimized A_throat:   \t{res['a_throat_cm2']:{FMT}} cm²")
		print(f"Optimized MR:         \t{res['mr']:{FMT}}")
		print("")
		print(f"Apogee:               \t{res['apogee_m']:{FMT}} m")
		print(f"Burn time:            \t{res['burn_time_s']:{FMT}} s")
		print(f"Liftoff thrust:       \t{res['thrust_N']:{FMT}} N")
		print(f"Liftoff Isp:          \t{res['isp_s']:{FMT}} s")
		print(f"Chamber pressure:     \t{res['p_chamber_bar']:{FMT}} bar")
		print(f"Injector ΔP:          \t{res['delta_p_bar']:{FMT}} bar")
		print("")
		print(f"Dry mass:             \t{res['m_dry_kg']:{FMT}} kg")
		print(f"Pressurant mass:      \t{res['m_press_kg']:{FMT}} kg")
		print(f"Total mass at liftoff:\t{res['m_initial_kg']:{FMT}} kg")
		print(f"TWR at launch:        \t{res['twr_launch']:{FMT}}")

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
		"""Draw all the connectivity graphs"""

		os.makedirs(out_dir, exist_ok=True)
		viewer = GraphViewer(self.model)
		for gtype in ["dataflow", "tree", "cycle"]:
			viewer.write_graph(
				gtype     = gtype,
				display   = False,
				show_vars = True,
				outfile   = os.path.join(out_dir, f"{prefix}_{gtype}.png"),
			)

	def report(self, res: dict, out_txt: str = "outputs/rocket.txt"):
		"""Print results and generate output artifacts"""

		self.print_summary(res)
		self.print_parameters(out_txt)
		self.print_graphs()
	#endregion
