#region Imports
import numpy as np

from typing          import TYPE_CHECKING
from .helpers        import to_cea_reactant
from scipy.constants import g

if TYPE_CHECKING: from .reac import Reactant
#endregion

class CEABackend:
	"""NASA CEA v3 native Python backend with in-memory execution"""

	def __init__(
		self,
		ox_reactants   : tuple["Reactant", ...],
		fuel_reactants : tuple["Reactant", ...],
	):
		import cea
		self._cea = cea
		self.ox_reactants   = ox_reactants
		self.fuel_reactants = fuel_reactants

		all_cea = (
			[to_cea_reactant(r) for r in ox_reactants]
			+ [to_cea_reactant(r) for r in fuel_reactants]
		)

		self._reac_mix = cea.Mixture(all_cea)
		self._prod_mix = cea.Mixture(all_cea, products_from_reactants=True)
		self._solver   = cea.RocketSolver(
			self._prod_mix, reactants=self._reac_mix
		)
		self._solution = cea.RocketSolution(self._solver)
		ox_tot   = sum(r.mass_fraction for r in ox_reactants)
		fuel_tot = sum(r.mass_fraction for r in fuel_reactants)
		self._ox_norm = np.array(
			[r.mass_fraction / ox_tot for r in ox_reactants]
		)
		self._fuel_norm = np.array(
			[r.mass_fraction / fuel_tot for r in fuel_reactants]
		)
		self._temps = np.array(
			[r.temperature for r in ox_reactants]
			+ [r.temperature for r in fuel_reactants]
		)
		self._last_state: tuple[float, float, float] | None = None

	def _solve(self, pc_pa: float, mr: float, eps: float = 5.0):
		state = (float(np.real(pc_pa)), float(np.real(mr)), float(np.real(eps)))

		if self._last_state == state: return

		w_ox   = self._ox_norm   * (state[1] / (state[1] + 1.0))
		w_fuel = self._fuel_norm * (1.0 / (state[1] + 1.0))

		weights = np.concatenate([w_ox, w_fuel])
		h = self._reac_mix.calc_property(self._cea.ENTHALPY, weights, self._temps)

		self._solver.solve(
			self._solution, weights, state[0], 1.0e5,
			supar=[state[2]], hc=h / self._cea.R, iac=True,
		)

		self._last_state = state

	def get_cstar(self, pc_pa: float, mr: float) -> float:
		self._solve(pc_pa, mr, eps=5.0)
		return float(self._solution.c_star[0])

	def get_tcomb(self, pc_pa: float, mr: float) -> float:
		self._solve(pc_pa, mr, eps=5.0)
		return float(self._solution.T[0])

	def get_isp(
		self, pc_pa: float, mr: float, eps: float, p_amb_pa: float = 101325.0
	) -> float:
		self._solve(pc_pa, mr, eps=eps)

		cstar   = float(self._solution.c_star[0])
		isp_vac = float(self._solution.Isp_vacuum[-1]) / g

		if p_amb_pa > 0.0:
			return isp_vac - (p_amb_pa * eps * cstar) / (pc_pa * g)

		return isp_vac

