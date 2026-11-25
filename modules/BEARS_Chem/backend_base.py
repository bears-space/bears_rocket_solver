#region Imports
from dataclasses import dataclass
from typing      import Protocol, runtime_checkable
#endregion

@dataclass(frozen=True)
class CombustionState:
	"""Equilibrium combustion result, in SI units"""
	isp        : float  # Ideal sea-level specific impulse [s]
	t_chamber  : float  # Adiabatic flame temperature in the chamber [K]
	molar_mass : float  # Molar mass of the chamber gas [kg/mol]
	gamma      : float  # Ratio of specific heats of the chamber gas [-]

@runtime_checkable
class ThermochemistryBackend(Protocol):
	"""Chemical equilibrium solver"""

	def evaluate(
		self,
		pc_pa : float,  # Chamber pressure [Pa]
		mr    : float,  # Mixture ratio, oxidizer over fuel mass flow [-]
		eps   : float,  # Nozzle expansion ratio A_exit / A_throat [-]
	) -> CombustionState: ...
