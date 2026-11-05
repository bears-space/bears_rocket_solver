#region Imports
from typing import Protocol, runtime_checkable
#endregion

@runtime_checkable
class ThermochemistryBackend(Protocol):
	"""Abstract protocol for chemical equilibrium backends"""

	def get_cstar(self, pc_pa: float, mr: float) -> float:
		...

	def get_tcomb(self, pc_pa: float, mr: float) -> float:
		...

	def get_isp(
		self,
		pc_pa    : float,
		mr       : float,
		eps      : float,
		p_amb_pa : float = 101325.0,
	) -> float:
		...
