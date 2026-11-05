# region Imports
import os

from pathlib import Path
from typing  import Any

from ..Config import BipropellantConfig

from .reac         import Reactant
from .helpers      import bulk_density
from .backend_base import ThermochemistryBackend
# endregion

class BEARS_Chem:
	"""Unified thermochemistry evaluation interface for OpenMDAO"""

	def __init__(
		self,
		backend  : ThermochemistryBackend,
		rho_ox   : float,
		rho_fuel : float,
	):
		self._backend = backend
		self.rho_ox   = rho_ox
		self.rho_fuel = rho_fuel

	@property
	def _cea(self) -> Any:
		if hasattr(self._backend, "_cea"):
			return self._backend._cea
		return self._backend

	@classmethod
	def set_work_dir(cls, path: str | Path):
		try:
			import rocketcea.cea_obj as cea_obj
			abs_path = os.path.abspath(path)
			os.makedirs(abs_path, exist_ok=True)
			cea_obj.ROCKETCEA_DATA_DIR = abs_path
		except ImportError:
			pass

	@classmethod
	def from_config(
		cls,
		config   : BipropellantConfig,
		backend  : str = "auto",
		work_dir : str | Path | None = None,
	) -> "BEARS_Chem":
		if work_dir is not None:
			cls.set_work_dir(work_dir)

		ox_reactants   = tuple(Reactant.from_config(r) for r in config.oxidizers)
		fuel_reactants = tuple(Reactant.from_config(r) for r in config.fuels)

		rho_ox   = bulk_density(ox_reactants)
		rho_fuel = bulk_density(fuel_reactants)

		selected = backend.lower()
		if selected == "auto":
			try:
				import cea
				selected = "cea"
			except ImportError:
				selected = "rocketcea"

		if selected == "cea":
			from .backend_cea import CEABackend
			engine = CEABackend(ox_reactants, fuel_reactants)
		elif selected == "rocketcea":
			from .backend_rocketcea import RocketCEABackend
			engine = RocketCEABackend(ox_reactants, fuel_reactants, work_dir)
		else:
			raise ValueError(f"Unknown thermochemistry backend: '{backend}'")

		return cls(engine, rho_ox, rho_fuel)

	def get_cstar(self, pc_pa: float, mr: float) -> float:
		return self._backend.get_cstar(pc_pa, mr)

	def get_tcomb(self, pc_pa: float, mr: float) -> float:
		return self._backend.get_tcomb(pc_pa, mr)

	def get_isp(
		self,
		pc_pa    : float,
		mr       : float,
		eps      : float,
		p_amb_pa : float = 101325.0,
	) -> float:
		return self._backend.get_isp(pc_pa, mr, eps, p_amb_pa)
