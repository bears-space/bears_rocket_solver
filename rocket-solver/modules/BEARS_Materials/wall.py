#region Imports
from math        import pi
from dataclasses import dataclass

import numpy as np

from .material import Material
#endregion

@dataclass(frozen=True)
class Layer:
	material:        Material
	thickness:       float | None = None # None = sized for pressure
	is_load_bearing: bool = True # False for thermal insulation

	@property
	def is_dynamic(self) -> bool:
		return self.thickness is None

class LayeredWall:

	def __init__(self, *layers: Layer):
		if not layers:
			raise ValueError("A LayeredWall must have at least one layer")

		dynamic_count = sum(1 for layer in layers if layer.is_dynamic)

		if dynamic_count > 1:
			raise ValueError("At most one Layer can be sized dynamically")

		self.layers = list(layers)

	def size_layers(self, p_max, r_out, sf):

		p_fixed = 0.0

		for layer in self.layers:
			if not layer.is_dynamic and layer.is_load_bearing:
				sigma_safe = layer.material.yield_strength / sf
				p_fixed += (sigma_safe * layer.thickness) / r_out

		diff_p = p_max - p_fixed

		if np.iscomplexobj(diff_p):
			p_rem = diff_p if diff_p.real > 0.0 else 0.0
		else:
			p_rem = max(0.0, diff_p)

		thicknesses = []
		for layer in self.layers:
			if layer.is_dynamic:
				sigma_safe = layer.material.yield_strength / sf
				t = (p_rem * r_out) / (sigma_safe + p_rem)
			else:
				t = layer.thickness

			thicknesses.append(t)

		return thicknesses

	def compute_masses(self, thicknesses, r_in, l_cyl):
		masses = []
		r_inner = r_in
		for layer, t in zip(self.layers, thicknesses):
			r_outer = r_inner + t
			v_cyl   = pi * (r_outer**2 - r_inner**2) * l_cyl
			v_caps  = (4.0 / 3.0) * pi * (r_outer**3 - r_inner**3)
			masses.append((v_cyl + v_caps) * layer.material.density)
			r_inner = r_outer

		return sum(masses), masses


