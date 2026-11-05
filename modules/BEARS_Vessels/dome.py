#region Constants
# Isotensoid dome factors
# kV: ratio of enclosed dome volume to cylinder radius cubed (V = 2 * kV * r^3)
# kL: ratio of dome depth along axis to cylinder radius (L = kL * r)
K_V_ISOTENSOID: float = 1.4341
K_L_ISOTENSOID: float = 0.6276
#endregion

#region Geometry functions
def dome_shell_volume(
	r_inner: float,
	r_outer: float,
	k_v: float = K_V_ISOTENSOID
) -> float:
	return 2.0 * k_v * (r_outer**3 - r_inner**3)

def dome_length(r: float, k_l: float = K_L_ISOTENSOID) -> float:
	return k_l * r
#endregion
