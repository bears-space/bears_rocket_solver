# region Imports
import os
import rocketcea.cea_obj as cea_obj

from pathlib               import Path
from rocketcea.input_cards import oxCards, fuelCards
from rocketcea.cea_obj     import CEA_Obj, add_new_fuel, add_new_oxidizer

from ..Config import MixtureConfig

from .reac    import Reactant
from .helpers import gencard, bulk_density
# endregion

pa_to_psia = 1.450377e-4 # 1 Pa = 1.45038e-4 psia
fts_to_ms  = 0.3048      # 1 ft/s = 0.3048 m/s

class Thermochemistry:

	def __init__(self, cea: CEA_Obj, rho_ox: float, rho_fuel: float):
		self._cea     = cea
		self.rho_ox   = rho_ox
		self.rho_fuel = rho_fuel

	@classmethod
	def set_work_dir(cls, path: str | Path):
		abs_path = os.path.abspath(path)
		os.makedirs(abs_path, exist_ok=True)
		cea_obj.ROCKETCEA_DATA_DIR = abs_path

	@classmethod
	def from_config(
		cls,
		config   : MixtureConfig,
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
			reactants = [Reactant.from_config(r) for r in rlist]

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
		return self._cea.get_Cstar(Pc=pc_pa * pa_to_psia, MR=mr) * fts_to_ms

	def get_isp(self, pc_pa: float, mr: float, eps: float) -> float:
		return self._cea.get_Isp(Pc=pc_pa * pa_to_psia, MR=mr, eps=eps)

	def get_tcomb(self, pc_pa: float, mr: float) -> float:
		return self._cea.get_Tcomb(Pc=pc_pa * pa_to_psia, MR=mr) * (5.0 / 9.0)
