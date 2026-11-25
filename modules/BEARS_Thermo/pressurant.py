"""
Pressurant mass needed to push the oxidizer out of its tank

The pressurant gas expands from its bottle into the oxidizer tank ullage
through a regulator. It has to fill the ullage above the oxidizer vapor
pressure (pad gas) and then replace the oxidizer volume as it drains (burn
gas). See doc/pressurant_blowdown_thermodynamics.pdf
"""

#region Imports
from dataclasses    import dataclass
from importlib.util import find_spec
from typing         import Protocol, runtime_checkable

import numpy as np

from ..Config        import Gas, Scalar
from ..BEARS_Vessels import ullage_volume
#endregion

# Pressure steps of the real-gas blowdown integration
COOLPROP_STEPS = 40

#region Interface
@dataclass(frozen=True)
class BlowdownResult:
	"""Pressurant sizing, in SI units"""
	m_press     : Scalar   # Pressurant mass to load, margin included [kg]
	rho_press   : Scalar   # Pressurant density in the full bottle [kg/m^3]
	m_pad       : Scalar   # Pad gas above vapor pressure in ullage [kg]
	m_burn      : Scalar   # Gas that replaces the drained oxidizer [kg]
	f_delivered : Scalar   # Delivered share of initial bottle mass [-]

@runtime_checkable
class PressurantThermoModel(Protocol):
	"""Pressurant blowdown model"""
	supports_complex_step : bool # True if `compute` accepts complex inputs

	def compute(
		self,
		gas      : Gas,    # Pressurant gas
		p_bottle : Scalar, # Bottle fill pressure [Pa]
		p_ox     : Scalar, # Regulated oxidizer tank pressure [Pa]
		p_margin : Scalar, # Bottle margin over p_ox at burnout [Pa]
		p_sat    : Scalar, # Oxidizer vapor pressure [Pa]
		t0       : Scalar, # Bottle temperature at fill [K]
		v_ox     : Scalar, # Oxidizer volume to replace [m^3]
		u_frac   : Scalar, # Oxidizer tank ullage fraction [-]
	) -> BlowdownResult: ...
#endregion

def _pad_pressure(p_ox: Scalar, p_sat: Scalar) -> Scalar:
	"""Partial pressure the pad gas adds over the vapor, clamped at 0 [Pa]"""
	diff = p_ox - p_sat
	if np.iscomplexobj(diff):
		return diff if diff.real > 0.0 else 0.0
	return max(0.0, diff)

#region Models
@dataclass(frozen=True)
class IdealGasBlowdown:
	"""Isentropic ideal-gas blowdown with a fixed bottle compressibility"""
	# Pressurant loaded over the computed need, as a factor [-]
	mass_margin           : float
	# Plain arithmetic, so complex step works
	supports_complex_step : bool = True

	def compute(
		self,
		gas      : Gas,
		p_bottle : Scalar,
		p_ox     : Scalar,
		p_margin : Scalar,
		p_sat    : Scalar,
		t0       : Scalar,
		v_ox     : Scalar,
		u_frac   : Scalar,
	) -> BlowdownResult:
		r, g = gas.r_specific, gas.gamma

		v_ull = ullage_volume(v_ox, u_frac)
		m_pad = _pad_pressure(p_ox, p_sat) * v_ull / (r * t0)

		# Isentropic expansion from the bottle down to the burnout pressure
		pr     = (p_ox + p_margin) / p_bottle
		f_del  = 1.0 - pr ** (1.0 / g)
		t_mean = (t0 / g) * (1.0 - pr) / f_del
		m_burn = (p_ox * v_ox) / (r * t_mean)

		m_press = self.mass_margin * (m_burn + m_pad) / f_del
		rho     = p_bottle / (gas.z_factor * r * t0)
		return BlowdownResult(m_press, rho, m_pad, m_burn, f_del)

@dataclass(frozen=True)
class CoolPropBlowdown:
	"""
	Real-gas blowdown with CoolProp properties

	CoolProp only takes real numbers, so this model needs finite-difference
	partials instead of complex step
	"""
	# Pressurant loaded over the computed need, as a factor [-]
	mass_margin           : float
	# CoolProp is real-valued only
	supports_complex_step : bool = False

	def compute(
		self,
		gas      : Gas,
		p_bottle : Scalar,
		p_ox     : Scalar,
		p_margin : Scalar,
		p_sat    : Scalar,
		t0       : Scalar,
		v_ox     : Scalar,
		u_frac   : Scalar,
	) -> BlowdownResult:
		from CoolProp.CoolProp import PropsSI
		from scipy.optimize    import brentq

		fl       = gas.coolprop_name
		t0       = float(np.real(t0))
		p_bottle = float(np.real(p_bottle))
		p_ox     = float(np.real(p_ox))
		v_ox     = float(v_ox)
		p_end = p_ox + float(np.real(p_margin))

		# Isentropic expansion of the bottle, and the mean enthalpy of the gas
		# that leaves it
		rho0  = PropsSI("D", "T", t0, "P", p_bottle, fl)
		s0    = PropsSI("S", "T", t0, "P", p_bottle, fl)
		ps    = np.linspace(p_bottle, p_end, COOLPROP_STEPS)
		rhos  = np.array([PropsSI("D", "P", p, "S", s0, fl) for p in ps])
		hs    = np.array([PropsSI("H", "P", p, "S", s0, fl) for p in ps])
		dm    = rhos[:-1] - rhos[1:]
		h_in  = float(np.sum(0.5 * (hs[:-1] + hs[1:]) * dm) / np.sum(dm))
		f_del = float(1.0 - rhos[-1] / rho0)

		# Energy balance of the ullage as it grows from its loaded volume to
		# the full tank, solved for the final gas temperature
		v_u0 = float(np.real(ullage_volume(v_ox, u_frac)))
		v_u1 = v_u0 + v_ox
		rho1 = PropsSI("D", "T", t0, "P", p_ox, fl)
		u1   = PropsSI("U", "T", t0, "P", p_ox, fl)
		m1   = rho1 * v_u0

		def energy_residual(temp: float) -> float:
			rho2 = PropsSI("D", "T", temp, "P", p_ox, fl)
			u2   = PropsSI("U", "T", temp, "P", p_ox, fl)
			m2   = rho2 * v_u1
			return m2 * u2 - (m1 * u1 + (m2 - m1) * h_in - p_ox * v_ox)

		# Bracket for the final ullage temperature [K]
		t2 = float(brentq(energy_residual, 150.0, 1.5 * t0))

		m_burn  = PropsSI("D", "T", t2, "P", p_ox, fl) * v_u1 - m1
		p_pad   = _pad_pressure(p_ox, float(np.real(p_sat)))
		m_pad   = p_pad * v_u0 / (gas.r_specific * t0)
		m_press = self.mass_margin * (m_burn + m_pad) / f_del
		return BlowdownResult(m_press, rho0, m_pad, m_burn, f_del)
#endregion

def create_pressurant_thermo(
	backend     : str,
	mass_margin : float
) -> PressurantThermoModel:
	"""Blowdown model for the [models] pressurant_thermo choice"""
	if backend == "auto":
		backend = "coolprop" if find_spec("CoolProp") is not None else "ideal"

	match backend:
		case "coolprop":
			return CoolPropBlowdown(mass_margin)
		case "ideal":
			return IdealGasBlowdown(mass_margin)
		case _:
			raise ValueError(
				f"Unknown pressurant_thermo backend: '{backend}'"
			)
