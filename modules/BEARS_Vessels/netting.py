"""
Thin-wall thickness of a pressure-loaded cylinder layer, see
doc/hoop_stress_derivation.pdf
"""

#region Imports
from ..Config import DiffFloat
#endregion

def size_composite_layer(
	p_design   : DiffFloat,
	r_out      : DiffFloat,
	sigma_safe : DiffFloat,
	cos_sq     : DiffFloat,
	tan_sq     : DiffFloat,
	v_f        : DiffFloat,
) -> DiffFloat:
	"""
	Thickness [m] of a filament-wound layer by netting theory: helical fibers
	at angle alpha carry the axial load, hoop fibers the remaining hoop load

	p_design   : pressure the layer has to hold [Pa]
	r_out      : outer tank radius [m]
	sigma_safe : allowable fiber stress [Pa]
	cos_sq     : cos^2(alpha) of the helical winding angle [-]
	tan_sq     : tan^2(alpha) of the helical winding angle [-]
	v_f        : fiber volume fraction [-]
	"""
	t_hel  = (p_design * r_out) / (2.0 * sigma_safe * cos_sq)
	t_hoop = (p_design * r_out / sigma_safe) * (1.0 - 0.5 * tan_sq)
	return (t_hel + t_hoop) / v_f

def size_metal_layer(
	p_design   : DiffFloat,
	r_out      : DiffFloat,
	sigma_safe : DiffFloat,
) -> DiffFloat:
	"""
	Thickness [m] of an isotropic layer from the hoop stress

	p_design   : pressure the layer has to hold [Pa]
	r_out      : outer tank radius [m]
	sigma_safe : allowable stress [Pa]
	"""
	return (p_design * r_out) / (sigma_safe + p_design)
