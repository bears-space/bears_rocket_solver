"""
Thickness and mass of a layered tank wall

Layers with a fixed thickness hold part of the pressure, and the one layer
without a thickness, if any, is sized to hold the rest
"""

#region Imports
from math import pi, cos, tan

import numpy as np

from ..Config import (
	CompositeLayer,
	MetalLayer,
	Wall,
	DiffFloat,
	clamp_nonneg,
)

from .dome    import domes_shell_volume
from .netting import size_composite_layer, size_metal_layer
#endregion

def allowable_stress(
	layer         : MetalLayer | CompositeLayer,
	safety_factor : DiffFloat,
) -> DiffFloat:
	"""
	Stress the layer may carry [Pa]:
	yield for metals, realized fiber strength for composites
	"""
	match layer:
		case CompositeLayer():
			ult = layer.material.ultimate_strength
			return ult * layer.efficiency / safety_factor
		case MetalLayer():
			return layer.material.yield_strength / safety_factor

def size_layers(
	wall          : Wall,
	p_max         : DiffFloat,
	r_out         : DiffFloat,
	safety_factor : DiffFloat,
) -> tuple[DiffFloat, ...]:
	"""Thickness of each layer [m], inside out, to hold `p_max` [Pa]"""

	# Pressure the fixed layers already hold. A composite layer is credited
	# with 1 / 1.5 of what a metal layer of the same allowable stress holds
	p_fixed: DiffFloat = 0.0
	for layer in wall.layers:
		if layer.thickness is None:
			continue
		sigma = allowable_stress(layer, safety_factor)
		match layer:
			case CompositeLayer():
				p_fixed += sigma * layer.thickness / (1.5 * r_out)
			case MetalLayer():
				p_fixed += sigma * layer.thickness / r_out

	# Pressure left for the sized layer, never negative
	p_rem = clamp_nonneg(p_max - p_fixed)

	thicknesses: list[DiffFloat] = []
	for layer in wall.layers:
		if layer.thickness is not None:
			thicknesses.append(layer.thickness)
			continue

		sigma = allowable_stress(layer, safety_factor)
		match layer:
			case CompositeLayer():
				t = size_composite_layer(
					p_rem, r_out, sigma,
					cos(layer.helical_angle)**2,
					tan(layer.helical_angle)**2,
					layer.fiber_volume_frac,
				)
			case MetalLayer():
				t = size_metal_layer(p_rem, r_out, sigma)
		thicknesses.append(t)

	return tuple(thicknesses)

def layer_masses(
	wall        : Wall,
	thicknesses : tuple[DiffFloat, ...],
	r_in        : DiffFloat,
	l_cyl       : DiffFloat,
) -> tuple[DiffFloat, ...]:
	"""
	Mass of each layer [kg], from the inside out, over the cylinder of length
	`l_cyl` [m] and both domes, for the inner tank radius `r_in` [m]
	"""
	masses: list[DiffFloat]  = []
	r_inner = r_in
	for layer, t in zip(wall.layers, thicknesses):
		r_outer = r_inner + t
		v_cyl   = pi * (r_outer**2 - r_inner**2) * l_cyl
		v_domes = domes_shell_volume(r_inner, r_outer)
		masses.append((v_cyl + v_domes) * layer.material.density)
		r_inner = r_outer

	return tuple(masses)
