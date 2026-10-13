#region Imports
import pydot
#endregion

#region Graph Stylizer
def style_graph(
	dot         : pydot.Dot,
	rankdir     : str = "LR",
	splines     : str = "ortho",
	concentrate : bool = True,
	dpi         : int = 300,
) -> pydot.Dot:
	"""Apply presentation styling and clean routing to a pydot graph."""
	dot.set_rankdir(rankdir)
	dot.set("splines",     splines)
	dot.set("concentrate", "true" if concentrate else "false")
	dot.set("dpi",         str(dpi))
	dot.set("fontname",    "Helvetica")
	dot.set("fontsize",    "11")
	dot.set("nodesep",     "0.4")
	dot.set("ranksep",     "0.7")
	dot.set("pad",         "0.3")

	def restyle_subgraph(sg):
		if isinstance(sg, pydot.Cluster):
			sg.set("style",     "rounded,filled")
			sg.set("fillcolor", "#f8f9fa")
			sg.set("color",     "#adb5bd")
			sg.set("penwidth",  "1.5")
			sg.set("fontname",  "Helvetica-Bold")
			sg.set("fontsize",  "12")

		for node in sg.get_nodes():
			name = node.get_name().strip('"')
			if name in ("_Incoming", "_Outgoing"):
				continue
			node.set("fontname", "Helvetica")
			node.set("fontsize", "10")
			node.set("style",    "rounded,filled")
			node.set("penwidth", "1.2")

			if "DesignVars" in name or "OptimizationVars" in name:
				node.set("fillcolor", "#e7f5ff")
				node.set("color",     "#1c7ed6")
				node.set("fontcolor", "#1864ab")
			elif "Tank" in name or "Prop" in name:
				node.set("fillcolor", "#e6fcf5")
				node.set("color",     "#0ca678")
				node.set("fontcolor", "#087f5b")
			elif "Trajectory" in name or "Sensors" in name:
				node.set("fillcolor", "#f3f0ff")
				node.set("color",     "#7048e8")
				node.set("fontcolor", "#5f3dc4")
			elif "Mass" in name:
				node.set("fillcolor", "#fff4e6")
				node.set("color",     "#fd7e14")
				node.set("fontcolor", "#d9480f")

		for edge in sg.get_edges():
			edge.set("color",    "#495057")
			edge.set("penwidth", "1.1")
			edge.set("arrowsize", "0.7")

		for child in sg.get_subgraphs():
			restyle_subgraph(child)

	restyle_subgraph(dot)
	return dot
#endregion
