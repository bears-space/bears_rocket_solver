#region Imports
from math import pi, cos, tan, radians
import numpy as np
#endregion

#region Clairaut
def clairaut_angle_trig(r_boss: float, r_out: float) -> tuple[float, float]:
	sin_a = r_boss / r_out
	cos_sq = 1.0 - sin_a**2
	tan_sq = sin_a**2 / cos_sq
	return cos_sq, tan_sq
#endregion

#region Sizing
def size_composite_layer(
	p_design: float,
	r_out: float,
	sigma_safe: float,
	cos_sq: float,
	tan_sq: float,
	v_f: float
) -> float:
	t_hel = (p_design * r_out) / (2.0 * sigma_safe * cos_sq)
	t_hoop = (p_design * r_out / sigma_safe) * (1.0 - 0.5 * tan_sq)
	return (t_hel + t_hoop) / v_f

def size_metal_layer(
	p_design: float,
	r_out: float,
	sigma_safe: float
) -> float:
	return (p_design * r_out) / (sigma_safe + p_design)
#endregion
