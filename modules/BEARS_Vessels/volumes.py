#region Imports
from ..Config import DiffFloat
#endregion

def tank_internal_volume(
	v_fluid     : DiffFloat,
	ullage_frac : DiffFloat,
) -> DiffFloat:
	"""
	Internal tank volume [m^3] for a fluid volume `v_fluid` [m^3] and an
	ullage fraction `ullage_frac` of the tank volume [-]
	"""
	return v_fluid / (1.0 - ullage_frac)

def ullage_volume(v_fluid: DiffFloat, ullage_frac: DiffFloat) -> DiffFloat:
	"""Gas-filled volume of the tank at loading, u * V_tank [m^3]"""
	return ullage_frac * tank_internal_volume(v_fluid, ullage_frac)
