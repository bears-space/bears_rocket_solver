"""
Shared numeric type aliases used across physics and component modules

All analytic physics functions accept complex numbers (and optionall NumPy
arrays) so OpenMDAO complex-step differentiation works without casts
"""

#region Imports
from typing import Any, TypeAlias

import numpy as np
from numpy.typing import NDArray
#endregion

#region Numeric types
Scalar  : TypeAlias = float | complex
Array   : TypeAlias = NDArray[np.floating[Any] | np.complexfloating[Any, Any]]
Numeric : TypeAlias = Scalar | Array
#endregion
