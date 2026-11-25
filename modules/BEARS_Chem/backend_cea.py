#region Imports
from typing import Any
import numpy as np

from ..Config      import CONSTANTS, Propellants, Species
from .backend_base import CombustionState
#endregion

# CEA takes bar and kJ/mol, and gives kg/kmol
J_PER_KJ                  = 1e3
PA_TO_BAR                 = 1e-5
KG_PER_KMOL_TO_KG_PER_MOL = 1e-3

def to_cea_reactant(species: Species) -> Any:
	"""NASA CEA reactant for a species"""
	import cea

	if species.enthalpy is None:
		return cea.Reactant(
			name        = species.name,
			formula     = species.formula,
			temperature = species.temperature,
		)

	return cea.Reactant(
		name           = species.name,
		formula        = species.formula,
		enthalpy       = species.enthalpy / J_PER_KJ,
		enthalpy_units = "kj/mol",
		temperature    = species.temperature,
	)

class CEABackend:
	"""NASA CEA v3 Python backend, solved in memory"""

	def __init__(self, propellants: Propellants) -> None:
		import cea
		self._cea = cea

		reactants = (propellants.oxidizer, *propellants.fuels)
		all_cea   = [to_cea_reactant(r) for r in reactants]

		self._reac_mix = cea.Mixture(all_cea)
		self._prod_mix = cea.Mixture(all_cea, products_from_reactants=True)
		self._solver   = cea.RocketSolver(
			self._prod_mix,
			reactants         = self._reac_mix,
			smooth_truncation = True,
		)
		self._solution = cea.RocketSolution(self._solver)

		# Mass shares of each fuel within the fuel blend
		fuel_total       = sum(f.mass_fraction for f in propellants.fuels)
		self._fuel_share = np.array([
			f.mass_fraction / fuel_total for f in propellants.fuels
		])
		self._temps      = np.array([r.temperature for r in reactants])

	def evaluate(
		self,
		pc_pa : float,
		mr    : float,
		eps   : float,
	) -> CombustionState:
		# CEA is real-valued only
		pc_pa = float(np.real(pc_pa))
		mr    = float(np.real(mr))
		eps   = float(np.real(eps))

		weights = np.concatenate([
			[mr / (mr + 1.0)],
			self._fuel_share / (mr + 1.0),
		])
		h = self._reac_mix.calc_property(
			self._cea.ENTHALPY, weights, self._temps,
		)

		# The stations are the chamber [0], the throat [1] and the nozzle exit
		# at area ratio eps [-1]
		sol = self._solution
		self._solver.solve(
			sol, weights, pc_pa * PA_TO_BAR,
			supar=[eps], hc=h / self._cea.R, iac=True,
		)

		# Vacuum Isp less the ambient pressure term, at sea level
		g0      = CONSTANTS.universal.standard_gravity
		p_amb   = CONSTANTS.atmosphere.sea_level_pressure
		cstar   = float(sol.c_star[0])
		isp_vac = float(sol.Isp_vacuum[-1]) / g0

		return CombustionState(
			isp        = isp_vac - (p_amb * eps * cstar) / (pc_pa * g0),
			t_chamber  = float(sol.T[0]),
			molar_mass = float(sol.MW[0]) * KG_PER_KMOL_TO_KG_PER_MOL,
			gamma      = float(sol.gamma_s[0]),
		)
