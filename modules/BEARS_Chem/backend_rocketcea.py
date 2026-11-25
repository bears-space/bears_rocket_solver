#region Imports
from ..Config      import CONSTANTS, Propellants, Species
from .backend_base import CombustionState
#endregion

# RocketCEA works in US customary units
PA_TO_PSIA                = 1.450377e-4
RANKINE_TO_KELVIN         = 5.0 / 9.0
KG_PER_KMOL_TO_KG_PER_MOL = 1e-3
J_PER_KJ                  = 1e3

def species_card(species: Species, wt_percent: float) -> str:
	"""
	CEA input card of one species at `wt_percent` of its blend, see
	<https://rocketcea.readthedocs.io/en/latest/std_examples.html>
	"""
	if species.enthalpy is None:
		raise ValueError(
			f"RocketCEA needs an enthalpy for the custom species "
			f"'{species.name}'"
		)

	atoms = " ".join(
		f"{atom} {float(count)}"
		for atom, count in species.formula.items()
	)
	return (
		f"{species.role} {species.name} {atoms} wt%={wt_percent}\n"
		f"h,kj/mol={species.enthalpy / J_PER_KJ} t(k)={species.temperature}"
	)

def blend_card(blend: tuple[Species, ...]) -> str:
	"""CEA input card of a blend with weights normalized to 100 %"""
	total = sum(s.mass_fraction for s in blend)
	return "\n".join(
		species_card(s, (s.mass_fraction / total) * 100.0)
		for s in blend
	)

class RocketCEABackend:
	"""RocketCEA backend, wrapping the Fortran CEA2"""

	def __init__(self, propellants: Propellants) -> None:
		from rocketcea.cea_obj     import CEA_Obj, add_new_fuel, add_new_oxidizer
		from rocketcea.input_cards import fuelCards, oxCards

		# Add blends RocketCEA does not know under joined names
		ox_blend  = (propellants.oxidizer,)
		ox_name   = "_".join(s.name for s in ox_blend)
		fuel_name = "_".join(s.name for s in propellants.fuels)
		if ox_name not in oxCards:
			add_new_oxidizer(ox_name, blend_card(ox_blend))
		if fuel_name not in fuelCards:
			add_new_fuel(fuel_name, blend_card(propellants.fuels))

		self._cea = CEA_Obj(oxName=ox_name, fuelName=fuel_name)

	def evaluate(
		self,
		pc_pa : float,
		mr    : float,
		eps   : float,
	) -> CombustionState:
		pc_psia    = pc_pa * PA_TO_PSIA
		p_amb_psia = CONSTANTS.atmosphere.sea_level_pressure * PA_TO_PSIA

		isp, _ = self._cea.estimate_Ambient_Isp(
			Pc=pc_psia, MR=mr, eps=eps, Pamb=p_amb_psia,
		)
		mw, gamma = self._cea.get_Chamber_MolWt_gamma(
			Pc=pc_psia, MR=mr,
		)
		t_rankine = float(self._cea.get_Tcomb(Pc=pc_psia, MR=mr))

		return CombustionState(
			isp        = float(isp),
			t_chamber  = t_rankine * RANKINE_TO_KELVIN,
			molar_mass = float(mw) * KG_PER_KMOL_TO_KG_PER_MOL,
			gamma      = float(gamma),
		)
