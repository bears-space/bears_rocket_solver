#region Imports
import os
import openmdao.api as om

from openmdao.api import Problem
from openmdao.visualization.graph_viewer import GraphViewer

from ..BEARS_Atmo import BEARS_Atm
from ..BEARS_Chem import Thermochemistry

from .group_rocket import RocketGroup
#endregion

class RocketLaunchProblem(Problem):

	def __init__(
		self,
		atm                 : BEARS_Atm,
		chem                : Thermochemistry,
		payload_mass        : float = 1.0,
		target_apogee       : float = 3100.0,
		ox_wall_material    = None,
		press_wall_material = None,
		**kwargs,
	):
		super().__init__(**kwargs)

		self.model = RocketGroup(
			atm=atm,
			chem=chem,
			ox_wall_material=ox_wall_material,
			press_wall_material=press_wall_material,
		)

		self.driver = om.ScipyOptimizeDriver()
		self.driver.options["optimizer"] = "SLSQP"

		# - Design variables

		# Store payload mass as an instance attribute
		self.payload_mass = payload_mass

		self.model.add_design_var(
			"OptimizationVars.o_propellant_mass",
			lower=1.0,
			upper=10.0,
			ref=5.0,
		)

		self.model.add_design_var(
			"OptimizationVars.o_mixture_ratio",
			lower=4.0,
			upper=10.0,
			ref=6.0,
		)

		self.model.add_design_var(
			"OptimizationVars.o_injector_area",
			lower=0.5e-5,
			upper=3.0e-5,
			ref=1.5e-5,
		)

		self.model.add_design_var(
			"OptimizationVars.o_nozzle_throat_area",
			lower=1.0e-4,
			upper=6.0e-4,
			ref=2.0e-4,
		)

		# - Constraints
		self.model.add_constraint(
			"apogee",
			lower=target_apogee,
			ref=target_apogee,
		)

		self.model.add_constraint(
			"burn_time",
			lower=2.0,
			upper=8.0,
			ref=5.0,
		)

		self.model.add_constraint(
			"Propulsion.prop_thrust",
			upper=1800.0,
			ref=1500.0,
		)

		# Injector pressure drop safety margin
		self.model.add_constraint(
			"Propulsion.injector_delta_p",
			lower=20.0,
			ref=20.0,
			units="bar",
		)

		# - Objective
		self.model.add_objective(
			"OptimizationVars.o_propellant_mass",
			ref=10.0,
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

		return {
			"m_prop_kg":     self.get_val("OptimizationVars.o_propellant_mass")[0],
			"mr":            self.get_val("OptimizationVars.o_mixture_ratio")[0],

			"a_inj_mm2": self.get_val(
				"OptimizationVars.o_injector_area",
				units="mm**2",
			)[0],

			"a_throat_cm2": self.get_val(
				"OptimizationVars.o_nozzle_throat_area",
				units="cm**2",
			)[0],

			"apogee_m":      self.get_val("apogee")[0],
			"burn_time_s":   self.get_val("burn_time")[0],
			"thrust_N":      self.get_val("Propulsion.prop_thrust")[0],
			"isp_s":         self.get_val("Propulsion.prop_isp")[0],
			"m_dry_kg":      self.get_val("Mass.dry_mass")[0],
			"m_initial_kg":  self.get_val("Mass.initial_mass")[0],

			"p_chamber_bar": self.get_val(
				"Propulsion.prop_chamber_pressure",
				units="bar",
			)[0],

			"delta_p_bar": self.get_val(
				"Propulsion.injector_delta_p",
				units="bar"
			)[0],
		}

	def print_summary(self, res: dict):

		FMT = "8.3f"

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
		print(f"Total mass at liftoff:\t{res['m_initial_kg']:{FMT}} kg")

	def print_parameters(self, path: str = "outputs/rocket.txt"):
		"""Dump all computed variables to an output file"""

		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, mode="wt") as f:
			self.model.list_outputs(
				val=True,
				units=True,
				hierarchical=True,
				out_stream=f,
			)

	def print_graphs(self, out_dir: str = "figures", prefix: str = "rocket"):
		"""Draw all the connectivity graphs"""

		os.makedirs(out_dir, exist_ok=True)
		viewer = GraphViewer(self.model)
		for gtype in ["dataflow", "tree", "cycle"]:
			viewer.write_graph(
				gtype=gtype,
				display=False,
				show_vars=True,
				outfile=os.path.join(out_dir, f"{prefix}_{gtype}.png"),
			)

	def report(self, res: dict, out_txt: str = "outputs/rocket.txt"):
		"""Print results and generate output artifacts"""

		self.print_summary(res)
		self.print_parameters(out_txt)
		self.print_graphs()
