#region Imports
from math import pi, cos, tan, radians
from dataclasses import dataclass
import numpy as np

from ..BEARS_Materials.material import Material
from .dome import K_V_ISOTENSOID, dome_shell_volume
from .netting import (
	clairaut_angle_trig,
	size_composite_layer,
	size_metal_layer,
)
#endregion

#region Layer record
@dataclass(frozen=True)
class Layer:
	material          : Material
	thickness         : float | None = None # None for pressure-sized
	is_load_bearing   : bool  = True        # False for thermal insulation
	helical_angle_deg : float | None = None # None for isotropic or dynamic boss
	efficiency        : float = 0.85        # Fiber translation efficiency
	fiber_volume_frac : float = 0.72        # Fiber volume fraction

	@property
	def is_dynamic(self) -> bool:
		return self.thickness is None

	@property
	def is_composite(self) -> bool:
		return self.helical_angle_deg is not None

	@classmethod
	def from_config(cls, cfg, materials: dict[str, Material]) -> "Layer":
		mat = materials.get(cfg.material_id)
		if mat is None:
			lower_map = {k.lower(): v for k, v in materials.items()}
			mat = lower_map.get(cfg.material_id.lower())

		if mat is None:
			avail = ", ".join(materials.keys())
			raise KeyError(
				f"Material '{cfg.material_id}' not found. "
				f"Available materials: {avail}"
			)

		return cls(
			material          = mat,
			thickness         = cfg.thickness_m,
			is_load_bearing   = cfg.is_load_bearing,
			helical_angle_deg = cfg.helical_angle_deg,
			efficiency        = cfg.efficiency,
			fiber_volume_frac = cfg.fiber_volume_frac,
		)
#endregion

#region LayeredWall
class LayeredWall:

	def __init__(self, *layers: Layer):
		if not layers:
			raise ValueError("A LayeredWall must have at least one layer")

		dynamic_count = sum(1 for layer in layers if layer.is_dynamic)
		if dynamic_count > 1:
			raise ValueError("At most one Layer can be sized dynamically")

		self.layers: tuple[Layer, ...] = tuple(layers)

	@classmethod
	def from_config(cls, cfg, materials: dict[str, Material]) -> "LayeredWall":
		layers = tuple(Layer.from_config(lay, materials) for lay in cfg.layers)
		return cls(*layers)

	def size_layers(self, p_max, r_out, sf, r_boss=None):
		p_fixed = 0.0

		for layer in self.layers:
			if not layer.is_dynamic and layer.is_load_bearing:
				if layer.is_composite:
					sigma_safe = (
						layer.material.ultimate_strength
						* layer.efficiency
						/ sf
					)
					p_fixed += (sigma_safe * layer.thickness) / (1.5 * r_out)
				else:
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
				if layer.is_composite:
					sigma_safe = (
						layer.material.ultimate_strength
						* layer.efficiency
						/ sf
					)
					if layer.helical_angle_deg is not None:
						alpha = radians(layer.helical_angle_deg)
						cos_sq, tan_sq = cos(alpha)**2, tan(alpha)**2
					elif r_boss is not None:
						cos_sq, tan_sq = clairaut_angle_trig(r_boss, r_out)
					else:
						cos_sq, tan_sq = 1.0, 0.0

					t = size_composite_layer(
						p_rem,
						r_out,
						sigma_safe,
						cos_sq,
						tan_sq,
						layer.fiber_volume_frac
					)
				else:
					sigma_safe = layer.material.yield_strength / sf
					t = size_metal_layer(p_rem, r_out, sigma_safe)
			else:
				t = layer.thickness

			thicknesses.append(t)

		return tuple(thicknesses)

	def compute_masses(
		self, thicknesses, r_in, l_cyl, k_v_dome=K_V_ISOTENSOID
	):
		masses = []
		r_inner = r_in
		for layer, t in zip(self.layers, thicknesses):
			r_outer = r_inner + t
			v_cyl   = pi * (r_outer**2 - r_inner**2) * l_cyl
			v_caps  = dome_shell_volume(r_inner, r_outer, k_v_dome)
			masses.append((v_cyl + v_caps) * layer.material.density)
			r_inner = r_outer

		return sum(masses), tuple(masses)
#endregion
