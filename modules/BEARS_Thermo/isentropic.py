"""
Isentropic flow relations of a calorically perfect ideal gas

Every ratio is static over total (stagnation) as a function of Mach number M
and specific heat ration gamma. All functions accept real or complex scalars
and NumPy arrays for complex-step OpenMDAO components

Reference: NASA Glenn Research Center, "Isentropic Flow Equations"
https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/isentrop/
"""

#region Imports
from typing import Any, TypeAlias

import numpy as np
from numpy.typing   import NDArray
from scipy.optimize import brentq
#endregion

#region Types
Scalar  : TypeAlias = float | complex
Array   : TypeAlias = NDArray[np.floating[Any] | np.complexfloating[Any, Any]]
Numeric : TypeAlias = Scalar | Array
#endregion

#region Helpers
def area_exponent(gamma: Numeric) -> Numeric:
	"""(gamma + 1) / (2 * (gamma - 1)), shared by A/A* and mass flow"""
	return (gamma + 1.0) / (2.0 * (gamma - 1.0))

def stagnation_factor(mach: Numeric, gamma: Numeric) -> Numeric:
	"""T_t / t = 1 + (gamma - 1) * M^2 / 2"""
	return 1.0 + 0.5 * (gamma - 1.0) * mach**2
#endregion

#region Export functions
def temperature_ratio(mach: Numeric, gamma: Numeric) -> Numeric:
	"""T / T_t = (1 + (gamma - 1) * M^2 / 2)^{-1}"""
	return 1.0 / stagnation_factor(mach, gamma)

def pressure_ratio(mach: Numeric, gamma: Numeric) -> Numeric:
	"""p / p_t = (T / T_t)^(gamma / (gamma - 1))"""
	return temperature_ratio(mach, gamma) ** (gamma / (gamma - 1.0))

def area_ratio(mach: Numeric, gamma: Numeric) -> Numeric:
	"""
	A / A* = (1 / M)
	       * [2 / (gamma + 1)
	          * (1 + (gamma - 1) * M^2 / 2)]^((gamma + 1) / (2 * (gamma - 1)))
	"""
	base = 2.0 / (gamma + 1.0) * stagnation_factor(mach, gamma)
	return base ** area_exponent(gamma) / mach

def mass_flow_parameter(mach: Numeric, gamma: Numeric) -> Numeric:
	"""
	Dimensionless mass flow per unit area (peaks at M=1, choked flow):

	  mdot * sqrt(R * T_t) / (A * p_t)
	    = sqrt(gamma) * M
	      * (1 + (gamma - 1) / 2 * M^2)^( -((gamma + 1) / (2 * (gamma - 1))) )
	"""
	return (
		np.sqrt(gamma) * mach
		* stagnation_factor(mach, gamma) ** -area_exponent(gamma)
	)
#endregion

#region Inverse
_M_MAX = 1e8 # Upper limit of the bracket search [-]

def _d_area_ratio(mach: Numeric, gamma: Numeric) -> Numeric:
	"""d(A/A*)/dM = A/A* * (M^2 - 1) / (M * (1 + (gamma - 1) / 2 * M^2))"""
	num = area_ratio(mach, gamma) * (mach**2 - 1.0)
	den = mach * stagnation_factor(mach, gamma)
	return num / den

def supersonic_mach_from_area_ratio(
	eps   : Numeric,
	gamma : Numeric,
) -> Numeric:
	"""
	Supersonic Mach number M >= 1 satisfying A / A* = eps

	Solves the real root with Brent's method. When eps or gamma is complex
	(complex step), one analytic Newton step propagates the imaginary part
	exactly
	"""
	if not np.all(np.real(eps) >= 1.0):
		raise ValueError(f"Area ratio A/A* must be >= 1 (got {eps})")

	def solve_real(eps_r: float, gamma_r: float) -> float:
		def residual(m: float) -> float:
			return float(area_ratio(m, gamma_r)) - eps_r

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
		mach  = mach - (area_ratio(mach, gamma) - eps) / slope

	return mach[()]
#endregion
