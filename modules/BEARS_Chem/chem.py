#region Imports
import os

from importlib.util import find_spec
from pathlib        import Path

from ..Config      import Propellants, Species
from .backend_base import CombustionState, ThermochemistryBackend
#endregion

def bulk_density(blend: tuple[Species, ...]) -> float:
	"""Density of a blend mixed by mass_fraction [kg/m^3]"""
	total = sum(s.mass_fraction for s in blend)
	return 1.0 / sum((s.mass_fraction / total) / s.density for s in blend)

class BEARS_Chem:
	"""Combustion chemistry of one propellant combination"""

	def __init__(self, propellants: Propellants, backend: str) -> None:
		"""`backend` is the [models] chem choice: auto, cea or rocketcea"""
		# Liquid oxidizer density [kg/m^3]
		self.rho_ox   = propellants.oxidizer.density
		# Fuel grain density [kg/m^3]
		self.rho_fuel = bulk_density(propellants.fuels)
		# Oxidizer saturation pressure [Pa]
		self.p_vap_ox = propellants.oxidizer.vapor_pressure

		if backend == "auto":
			backend = "cea" if find_spec("cea") else "rocketcea"

		self._backend: ThermochemistryBackend
		match backend:
			case "cea":
				from .backend_cea import CEABackend
				self._backend = CEABackend(propellants)
			case "rocketcea":
				from .backend_rocketcea import RocketCEABackend
				self._backend = RocketCEABackend(propellants)
			case _:
				raise ValueError(f"Unknown chemistry backend: '{backend}'")

	@staticmethod
	def set_work_dir(path: str | Path) -> None:
		"""Keep the RocketCEA scratch files in `path`, if installed"""
		if find_spec("rocketcea") is None: return

		import rocketcea.cea_obj as cea_obj
		abs_path = os.path.abspath(path)
		os.makedirs(abs_path, exist_ok=True)
		cea_obj.ROCKETCEA_DATA_DIR = abs_path

	def evaluate(
		self,
		pc_pa : float,
		mr    : float,
		eps   : float,
	) -> CombustionState:
		"""Equilibrium state at pc [Pa], mixture ratio and eps [-]"""
		return self._backend.evaluate(pc_pa, mr, eps)
