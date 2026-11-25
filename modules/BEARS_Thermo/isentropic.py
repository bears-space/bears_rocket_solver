"""
Isentropic flow relations of a calorically perfect ideal gas

Every ratio is static over total (stagnation) as a function of Mach number M
and specific heat ration gamma. All methods accept real or complex scalars
and NumPy arrays for complex-step OpenMDAO components

Reference: NASA Glenn Research Center, "Isentropic Flow Equations"
https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/isentrop/
"""

#region Imports
from dataclasses import dataclass
from typing      import Self

import numpy as np
from scipy.optimize import brentq

from ..Config            import Numeric
from ..Config.validation import require
#endregion

_M_MAX = 1e8 # Upper limit of the bracket search [-]

#region State
@dataclass(frozen=True)
class IsentropicState:
	"""
	Isentropic flow state of a caloricall perfect ideal gas

	Construct from Mach number with `from_mach`, or from supersonic area ratio
	A/A* >= 1 with `from_eps_sup`. All ratio properties are complex-step safe
	"""
	mach  : Numeric # Mach number M [-]
	gamma : Numeric # Ratio of specific heats cp/cv [-]

	def __post_init__(self) -> None:
		require(
			bool(np.all(np.real(self.gamma) > 1.0)),
			f"IsentropicState.gamma must be > 1 (got {self.gamma})",
		)
		require(
			bool(np.all(np.real(self.mach) >= 0.0)),
			f"IsentropicState.mach must be >= 0 (got {self.mach})",
		)

	@classmethod
	def from_mach(cls, mach: Numeric, gamma: Numeric) -> Self:
		"""Construct an isentropic state from Mach number and gamma"""
		return cls(mach=mach, gamma=gamma)

	@classmethod
	def from_eps_sup(cls, eps: Numeric, gamma: Numeric) -> Self:
		"""Construct a supersonic state (M >= 1) from area ratio A/A*"""
		require(
			bool(np.all(np.real(gamma) > 1.0)),
			f"IsentropicState.gamma must be > 1 (got {gamma})",
		)
		m = _solve_supersonic_mach(eps, gamma)
		return cls(mach=m, gamma=gamma)

	@property
	def t_ratio(self) -> Numeric:
		"""Static over total temperature T/T_t [-]"""
		return 1.0 / _stagnation_factor(self.mach, self.gamma)

	@property
	def p_ratio(self) -> Numeric:
		"""Static over total pressure p/p_t [-]"""
		return self.t_ratio ** (self.gamma / (self.gamma - 1.0))

	@property
	def area_ratio(self) -> Numeric:
		"""Local over sonic throat area A/A* [-]"""
		return _area_ratio(self.mach, self.gamma)

	@property
	def mfp(self) -> Numeric:
		"""Dimensionless mass flow parameter mdot*sqrt(R*T_t)(A*p_t) [-]"""
		stag = _stagnation_factor(self.mach, self.gamma)
		return (
			np.sqrt(self.gamma) * self.mach
			* stag ** -_area_exponent(self.gamma)
		)
#endregion

#region Inverse
def _solve_supersonic_mach(eps: Numeric, gamma: Numeric) -> Numeric:
	"""
	Supersonic Mach number M >= 1 satisfying A / A* = eps

	Solves the real root with Brent's method. When eps or gamma is complex
	(complex step), one analytic Newton step propagates the imaginary part
	exactly
	"""
	require(
		bool(np.all(np.real(eps) >= 1.0)),
		f"Area ratio A/A* must be >= 1 (got {eps})",
	)

	def solve_real(eps_r: float, gamma_r: float) -> float:
		def residual(m: float) -> float:
			return float(_area_ratio(m, gamma_r)) - eps_r

		if residual(1.0) == 0.0: return 1.0

		# Double the upper bracket until it holds the root
		m_hi = 2.0
		while residual(m_hi) < 0.0:
			m_hi *= 2.0
			if m_hi > _M_MAX:
				raise ValueError(
					f"No Mach number found for A/A* = {eps_r}"
				)

		return float(brentq(residual, 1.0, m_hi, xtol=1e-15, rtol=1e-15))

	mach = np.vectorize(solve_real, otypes=[float])(
		np.real(eps),
		np.real(gamma),
	)

	if np.iscomplexobj(eps) or np.iscomplexobj(gamma):
		slope = _d_area_ratio(mach, np.real(gamma))
		mach  = mach - (_area_ratio(mach, gamma) - eps) / slope

	return mach[()]
#endregion

#region Helpers

def _area_exponent(gamma: Numeric) -> Numeric:
	"""(gamma + 1) / (2 * (gamma - 1)), shared by A/A* and mass flow"""
	return (gamma + 1.0) / (2.0 * (gamma - 1.0))

def _stagnation_factor(mach: Numeric, gamma: Numeric) -> Numeric:
	"""T_t / T = 1 + (gamma - 1) * M^2 / 2"""
	return 1.0 + 0.5 * (gamma - 1.0) * mach**2

def _area_ratio(mach: Numeric, gamma: Numeric) -> Numeric:
	"""A / A* from Mach number and gamma"""
	base = 2.0 / (gamma + 1.0) * _stagnation_factor(mach, gamma)
	return base ** _area_exponent(gamma) / mach

def _d_area_ratio(mach: Numeric, gamma: Numeric) -> Numeric:
	"""d(A/A*)/dM = A/A* * (M^2 - 1) / (M * (1 + (gamma - 1) / 2 * M^2))"""
	num = _area_ratio(mach, gamma) * (mach**2 - 1.0)
	den = mach * _stagnation_factor(mach, gamma)
	return num / den
#endregion
