"""
Shared numeric types and differentiable helpers across physics modules

Analytic physics functions are polymorphic over real scalars and complex-step
dual numbers (`DiffFloat`) so OpenMDAO complex-step differentiation works
without casts or runtime wrappers
"""

#region Imports
from typing import TypeVar
#endregion

#region Types
# Differentiable scalar: real float or complex-step dual number
DiffFloat = TypeVar("DiffFloat", float, complex)
#endregion

#region Helpers
def clamp_nonneg(x: DiffFloat) -> DiffFloat:
	"""max(0, x) on the real part, preserving complex-step derivatives"""
	if isinstance(x, complex):
		return x if x.real > 0.0 else 0.0
	return max(0.0, x)
#endregion
