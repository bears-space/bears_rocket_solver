#region Imports
import os
import shutil

from importlib.util import find_spec

from openmdao.api import Group
from openmdao.visualization.graph_viewer import GraphViewer
#endregion

def write_output_table(model: Group, path: str) -> None:
	"""Write every computed model output, with its units, to a text file"""
	os.makedirs(os.path.dirname(path), exist_ok=True)
	with open(path, mode="wt") as f:
		model.list_outputs(
			val=True, units=True, hierarchical=True, out_stream=f,
		)

def write_graphs(model: Group, out_dir: str, prefix: str) -> None:
	"""
	Draw the dataflow, tree and cycle graphs of the model as PNGs, provided
	the Graphviz `dot` program and the pydot package are installed
	"""
	if shutil.which("dot") is None or find_spec("pydot") is None:
		print(
			f"Graphviz ('dot') or pydot not found, skipping {prefix} graphs"
		)
		return

	os.makedirs(out_dir, exist_ok=True)
	viewer = GraphViewer(model)
	for gtype in ["dataflow", "tree", "cycle"]:
		png_path = os.path.join(out_dir, f"{prefix}_{gtype}.png")
		dot = viewer.write_graph(
			gtype=gtype, display=False, show_vars=True, outfile=png_path,
		)
		if dot is None:
			continue

		# Left to right, with smooth edges merged where they run together
		dot.set_rankdir("LR")
		dot.set("splines",     "spline")
		dot.set("concentrate", "true")
		dot.write_png(png_path)
