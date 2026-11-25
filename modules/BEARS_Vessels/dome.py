"""
Geodesic isotensoid domes, one closing each end of a cylindrical tank

The dome shape scales with the cylinder radius r, so its enclosed volume and
axial depth are fixed multiples of r^3 and r. See
doc/geodesic_dome_derivation.pdf
"""

#region Imports
from ..Config import DiffFloat
#endregion

K_VOLUME = 1.4341  # Volume enclosed by one dome over r^3 [-]
K_LENGTH = 0.6276  # Axial depth of one dome over r [-]
N_DOMES  = 2       # One dome at each end of the tank

def domes_internal_volume(r_in: DiffFloat) -> DiffFloat:
	"""Volume enclosed by both domes [m^3], for inner radius `r_in` [m]"""
	return N_DOMES * K_VOLUME * r_in**3

def domes_length(r_in: DiffFloat) -> DiffFloat:
	"""Axial length of both domes [m], for inner radius `r_in` [m]"""
	return N_DOMES * K_LENGTH * r_in

def domes_shell_volume(r_inner: DiffFloat, r_outer: DiffFloat) -> DiffFloat:
	"""Material volume of both domes [m^3] between two radii [m]"""
	return N_DOMES * K_VOLUME * (r_outer**3 - r_inner**3)
