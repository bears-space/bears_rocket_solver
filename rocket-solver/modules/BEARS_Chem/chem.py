# region Imports
import os
import rocketcea.cea_obj as cea_obj

from pathlib               import Path
from rocketcea.input_cards import oxCards, fuelCards
from rocketcea.cea_obj     import CEA_Obj, add_new_fuel, add_new_oxidizer

from ..Config import BipropellantConfig

from .reac    import Reactant
from .helpers import gencard, bulk_density
# endregion

pa_to_psia = 1.450377e-4 # 1 Pa = 1.45038e-4 psia
fts_to_ms  = 0.3048      # 1 ft/s = 0.3048 m/s

class BEARS_Chem:

	def __init__(
		self,
		cea       : CEA_Obj,
		rho_ox    : float,
		rho_fuel  : float,
		eta_cstar : float = 0.85,
	):
		self._cea      = cea
		self.rho_ox    = rho_ox
		self.rho_fuel  = rho_fuel
		self.eta_cstar = eta_cstar

	@classmethod
	def set_work_dir(cls, path: str | Path):
		abs_path = os.path.abspath(path)
		os.makedirs(abs_path, exist_ok=True)
		cea_obj.ROCKETCEA_DATA_DIR = abs_path

	@classmethod
	def from_config(
		cls,
		config   : BipropellantConfig,
		work_dir : str | Path | None = None,
	) -> "Thermochemistry":
		if work_dir is not None:
			cls.set_work_dir(work_dir)

		reac_cards = {"oxid": oxCards, "fuel": fuelCards}

		rnames    : dict[str, str]   = {}
		densities : dict[str, float] = {}

		for rtype, rlist in [
			("oxid", config.oxidizers),
			("fuel", config.fuels),
		]:
			reactants = tuple(Reactant.from_config(r) for r in rlist)

			rname = "_".join([reac.name for reac in reactants])
			card = reac_cards[rtype]
			if rname not in card:
				card_text = gencard(reactants)
				if rtype == "fuel": add_new_fuel(rname, card_text)
				else: add_new_oxidizer(rname, card_text)
			rnames[rtype] = rname

			densities[rtype] = bulk_density(reactants)

		cea = CEA_Obj(oxName=rnames["oxid"], fuelName=rnames["fuel"])
		return cls(cea, densities["oxid"], densities["fuel"])

	def get_cstar(self, pc_pa: float, mr: float) -> float:
		#pc_safe = max(1.5e5, pc_pa)
		pc_safe = pc_pa
		cstar = self._cea.get_Cstar(Pc=pc_safe * pa_to_psia, MR=mr) * fts_to_ms
		return cstar * self.eta_cstar

	def get_isp(
		self,
		pc_pa    : float,
		mr       : float,
		eps      : float,
		p_amb_pa : float = 101325.0
	) -> float:
		#pc_safe = max(1.5e5, pc_pa)
		pc_safe = pc_pa
		pc_psia = pc_safe * pa_to_psia
		if p_amb_pa > 0.0:
			p_amb_psia = p_amb_pa * pa_to_psia
			isp, _ = self._cea.estimate_Ambient_Isp(
				Pc=pc_psia, MR=mr, eps=eps, Pamb=p_amb_psia
			)
		else:
			isp = self._cea.get_Isp(Pc=pc_psia, MR=mr, eps=eps)

		return float(isp) * self.eta_cstar

	def get_tcomb(self, pc_pa: float, mr: float) -> float:
		return self._cea.get_Tcomb(Pc=pc_pa * pa_to_psia, MR=mr) * (5.0 / 9.0)
