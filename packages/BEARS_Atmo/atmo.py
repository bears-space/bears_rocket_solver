#region imports
import numpy   as np
import isacalc as isa

from scipy.constants import g, R, zero_Celsius
#endregion

def atm_isa(h):
	std_atm = isa.Atmosphere()
	val = std_atm.calculate(h)

	# T, P, rho, a
	return val[1], val[2], val[3], val[4]

def atm_standalone(h):
	"""
	Standalone logic for ISA atmosphere

	NOTE: AI-generated placeholder
	"""

	T0 = 15.0 + zero_Celsius
	P0 = 101325.0
	L  = 0.0065
	M  = 0.0289644
	gamma = 1.4

	T = np.maximum(T0 - L * h, 216.65)
	P = P0 * (T / T0)**(g * M / (R * L))
	rho = P / ((R / M) * T)
	a = np.sqrt(gamma * (R / M) * T)

	return T, P, rho, a

model_map = {
	"isacalc": atm_isa,
	"standalone": atm_standalone
}

atmosphere_models = list(model_map.keys())

class BEARS_Atm:
	def __init__(self, model: str):
		self.model = model

	def __call__(self, altitude: float):
		return model_map[self.model](altitude)
