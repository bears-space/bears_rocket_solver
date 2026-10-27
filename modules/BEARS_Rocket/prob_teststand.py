#region Imports
import os
import openmdao.api as om

from openmdao.api import Problem
from openmdao.visualization.graph_viewer import GraphViewer

from ..BEARS_Chem import BEARS_Chem

from .group_teststand import TestStandGroup
from .graph_style     import style_graph

from .checks  import CheckFn, DEFAULT_TESTSTAND_CHECKS, run_checks
#endregion

class TestStandProblem(Problem):

	def __init__(
		self,
		chem   : BEARS_Chem,
		checks : tuple[CheckFn, ...] = DEFAULT_TESTSTAND_CHECKS,
		**kwargs,
	):
		super().__init__(**kwargs)

		self.chem  = chem
		self.model = TestStandGroup(chem=chem)

		self.checks = checks

	def setup(self, **kwargs):
		super().setup(**kwargs)

		# Run tank
		self.set_val("run_tank_pressure_PT2",  60.0,   units="bar")
		self.set_val("run_tank_diam",          0.15,   units="m")
		self.set_val("run_tank_ullage_frac",   0.08)
		self.set_val("run_tank_wall_density",  2700.0, units="kg/m**3")
		self.set_val("run_tank_yield_factor",  276e6,  units="Pa")
		self.set_val("run_tank_fluid_mass",    10.0,   units="kg")

		# Engine baseline parameters
		self.set_val("test_prop_mass_init",    8.0,    units="kg")
		self.set_val("test_mixture_ratio",     6.618)
		self.set_val("injector_area",          1.5e-5, units="m**2")
		self.set_val("injector_cd",            0.70)
		self.set_val("fuel_port_diam",         0.05,   units="m")
		self.set_val("fuel_reg_exponent",      0.50)
		self.set_val("fuel_reg_ref",           1.0e-4, units="m/s")
		self.set_val("nozzle_throat_area",     2.0e-4, units="m**2")
		self.set_val("nozzle_expansion_ratio", 5.0)
		self.set_val("nozzle_length",          0.15,   units="m")
		self.set_val("nozzle_eta_friction",    0.95)

		return self

	def set_opt_vars(
		self,
		m_prop_kg       : float | None = None,
		mr              : float | None = None,
		a_inj_mm2       : float | None = None,
		a_throat_cm2    : float | None = None,
		expansion_ratio : float | None = None,
	):
		if m_prop_kg is not None:
			self.set_val("test_prop_mass_init",    m_prop_kg,    units="kg")
		if mr is not None:
			self.set_val("test_mixture_ratio",     mr)
		if a_inj_mm2 is not None:
			self.set_val("injector_area",          a_inj_mm2,    units="mm**2")
		if a_throat_cm2 is not None:
			self.set_val("nozzle_throat_area",     a_throat_cm2, units="cm**2")
		if expansion_ratio is not None:
			self.set_val("nozzle_expansion_ratio", expansion_ratio)

	def run(self):
		self.run_model()
		return self

	#region Verification
	def verify(self, raise_on_error : bool = True):
		return run_checks(self, self.checks, raise_on_error=raise_on_error)
	#endregion

	#region Outputs
	def print_summary(self):

		FMT = "8.3f"

		self.verify()

		pt1 = 65.0
		tc1 = 288.15
		pt2 = self.get_val("Sensors.PT2_run_tank_pressure", units="bar")[0]
		tc2 = 275.15
		pt3 = self.get_val("test_chamber_pressure_PT3",     units="bar")[0]
		tc3 = self.get_val("test_chamber_temp_TC3",         units="K")[0]
		pt4 = 200.0
		tc4 = 285.15
		mr  = self.get_val("test_mixture_ratio")[0]
		thr = self.get_val("test_thrust",                   units="N")[0]
		isp = self.get_val("test_isp",                      units="s")[0]

		print("Simulating test stand:")
		print("")
		print(f"PT1 (N2O supply pressure):      \t{pt1:{FMT}} bar")
		print(f"TC1 (N2O supply temperature):   \t{tc1:{FMT}} K")
		print("")
		print(f"PT2 (run tank feed temperature):\t{pt2:{FMT}} bar")
		print(f"TC2 (run tank liquid temp):     \t{tc2:{FMT}} K")
		print("")
		print(f"PT3 (chamber pressure):         \t{pt3:{FMT}} bar")
		print(f"TC3 (chamber flame temp):       \t{tc3:{FMT}} K")
		print("")
		print(f"PT4 (N2 supply pressure):       \t{pt4:{FMT}} bar")
		print(f"TC4 (N2 supply pressure):       \t{tc4:{FMT}} K")
		print("")
		print(f"ΔP:                             \t{pt2 - pt3:{FMT}} bar")
		print(f"Thrust:                         \t{thr:{FMT}} N")
		print(f"Isp:                            \t{isp:{FMT}} s")

	def print_parameters(self, path: str = "outputs/rocket.txt"):
		os.makedirs(os.path.dirname(path), exist_ok=True)
		with open(path, mode="wt") as f:
			self.model.list_outputs(
				val=True,
				units=True,
				hierarchical=True,
				out_stream=f,
			)

	def print_graphs(
		self,
		out_dir : str = "figures",
		prefix  : str = "teststand",
	):
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
				splines = "ortho" if gtype != "tree" else "spline"
				#dot = style_graph(dot, splines=splines, concentrate=True)
				dot.write_png(png_path)

	def report(self, out_txt: str = "outputs/teststand.txt"):
		self.print_summary()
		self.print_parameters(out_txt)
		self.print_graphs()
	#endregion
