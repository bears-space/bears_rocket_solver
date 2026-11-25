"""
Isentropic flow relations of a calorically perfect ideal gas

Every ratio is static over total (stagnation) as a function of Mach number M
and specific heat ration gamma. All methods are polymorphic over real scalars
and complex-step dual numbers (`DiffFloat`)

Reference: NASA Glenn Research Center, "Isentropic Flow Equations"
https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/isentrop/
"""

#region Imports
from __future__ import annotations

from dataclasses import dataclass
from typing      import Generic

import numpy as np
from scipy.optimize import brentq

from ..Config            import DiffFloat
from ..Config.validation import require
#endregion

_M_MAX = 1e8 # Upper limit of the bracket search [-]

#region State
@dataclass(frozen=True)
class IsentropicState(Generic[DiffFloat]):
	"""
	Isentropic flow state of a calorically perfect ideal gas

	Construct using
	- the Mach number with `from_mach`, or
	- the supersonic area ratio A/A* >= 1 with `from_eps_sup`

	All properties are complex-step safe
	"""
	mach  : Numeric # Mach number M [-]
	gamma : Numeric # Ratio of specific heats cp/cv [-]

	def __post_init__(self) -> None:
		require(
			self.gamma.real > 1.0,
			f"IsentropicState.gamma must be > 1 (got {self.gamma})",
		)
		require(
			self.mach.real >= 0.0,
			f"IsentropicState.mach must be >= 0 (got {self.mach})",
		)

	@classmethod
	def from_mach(
		cls,
		mach  : DiffFloat,
		gamma : DiffFloat,
	) -> IsentropicState[DiffFloat]:
		"""Construct an isentropic state from Mach number and gamma"""
		return cls(mach=mach, gamma=gamma)

	@classmethod
	def from_eps_sup(
		cls,
		eps   : DiffFloat,
		gamma : DiffFloat,
	) -> IsentropicState[DiffFloat]:
		"""Construct a supersonic state (M >= 1) from area ratio A/A*"""
		require(
			gamma.real > 1.0,
			f"IsentropicState.gamma must be > 1 (got {gamma})",
		)
		m = _solve_supersonic_mach(eps, gamma)
		return cls(mach=m, gamma=gamma)

	@property
	def t_ratio(self) -> DiffFloat:
		"""Static over total temperature T/T_t [-]"""
		return 1.0 / _stagnation_factor(self.mach, self.gamma)

	@property
	def p_ratio(self) -> DiffFloat:
		"""Static over total pressure p/p_t [-]"""
		return self.t_ratio ** (self.gamma / (self.gamma - 1.0))

	@property
	def area_ratio(self) -> DiffFloat:
		"""Local over sonic throat area A/A* [-]"""
		return _area_ratio(self.mach, self.gamma)

	@property
	def mfp(self) -> DiffFloat:
		"""Dimensionless mass flow parameter mdot*sqrt(R*T_t)/(A*p_t) [-]"""
		stag = _stagnation_factor(self.mach, self.gamma)
		return (
			self.gamma**0.5 * self.mach
			* stag ** -_area_exponent(self.gamma)
		)
#endregion

#region Inverse
def _solve_supersonic_mach(
	eps   : DiffFloat,
	gamma : DiffFloat,
) -> DiffFloat:
	"""
	Supersonic Mach number M >= 1 satisfying A / A* = eps

	Solves the real root with Brent's method. When eps or gamma is complex
	(complex step), one analytic Newton step propagates the imaginary part
	exactly
	"""
	require(
		eps.real >= 1.0,
		f"Area ratio A/A* must be >= 1 (got {eps})",
	)

	eps_r   = eps.real
	gamma_r = gamma.real

	def residual(m: float) -> float:
		return _area_ratio(m, gamma_r) - eps_r

	if residual(1.0) == 0.0:
		mach_r = 1.0
	else:
		# Double the upper bracket until it holds the root
		m_hi = 2.0
		while residual(m_hi) < 0.0:
			m_hi *= 2.0
			if m_hi > _M_MAX:
				raise ValueError(
					f"No Mach number found for A/A* = {eps_r}"
				)
		mach_r = float(brentq(residual, 1.0, m_hi, xtol=1e-15, rtol=1e-15))

	if isinstance(eps, complex) or isinstance(gamma, complex):
		slope = _d_area_ratio(mach_r, gamma_r)
		return mach_r - (_area_ratio(mach_r, gamma) - eps) / slope

	return mach_r
#endregion

#region Helpers
def _area_exponent(gamma: DiffFloat) -> DiffFloat:
	"""(gamma + 1) / (2 * (gamma - 1)), shared by A/A* and mass flow"""
	return (gamma + 1.0) / (2.0 * (gamma - 1.0))

def _stagnation_factor(mach: DiffFloat, gamma: DiffFloat) -> DiffFloat:
	"""T_t / T = 1 + (gamma - 1) * M^2 / 2"""
	return 1.0 + 0.5 * (gamma - 1.0) * mach**2

def _area_ratio(mach: DiffFloat, gamma: DiffFloat) -> DiffFloat:
	"""A / A* from Mach number and gamma"""
	base = 2.0 / (gamma + 1.0) * _stagnation_factor(mach, gamma)
	return base ** _area_exponent(gamma) / mach

def _d_area_ratio(mach: DiffFloat, gamma: DiffFloat) -> DiffFloat:
	"""d(A/A*)/dM = A/A* * (M^2 - 1) / (M * (1 + (gamma - 1) / 2 * M^2))"""
	num = _area_ratio(mach, gamma) * (mach**2 - 1.0)
	den = mach * _stagnation_factor(mach, gamma)
	return num / den
#endregion
