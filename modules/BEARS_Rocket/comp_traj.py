#region Imports
from collections.abc import Sequence
from math            import pi

import numpy as np
from openmdao.api    import ExplicitComponent
from scipy.integrate import solve_ivp

from ..BEARS_Atmo import BEARS_Atm
from ..Config     import CONSTANTS, AerodynamicsConfig
#endregion

g = CONSTANTS.universal.standard_gravity  # Standard gravity [m/s^2]

# Integration settings of the flight phases
RTOL, ATOL   = 1e-7, 1e-9
COAST_SPAN_S = 1000.0  # Longest coast to integrate before apogee [s]

#region Ballistic functions
def drag_force(
	v    : float,
	diam : float,
	rho  : float,
	a    : float,
	aero : AerodynamicsConfig,
) -> float:
	"""
	Drag [N] at speed `v` [m/s] for the airframe diameter `diam` [m], air
	density `rho` [kg/m^3] and speed of sound `a` [m/s]
	"""
	area = pi * (diam / 2.0)**2
	cd   = float(np.interp(abs(v) / a, aero.drag_mach, aero.drag_cd))
	return 0.5 * rho * v**2 * cd * area

def ballistic_apogee(
	thrust : float,
	isp    : float,
	m_i    : float,
	m_prop : float,
	diam   : float,
	atm    : BEARS_Atm,
	aero   : AerodynamicsConfig,
) -> tuple[float, float]:
	"""
	Burn time [s] and apogee [m] of a vertical 1D flight

	thrust : constant thrust [N]
	isp    : constant Isp [s]
	m_i    : liftoff mass [kg]
	m_prop : burned propellant mass [kg]
	diam   : airframe diameter for the drag area [m]

	The boost and the coast are integrated separately, which avoids the jump
	in the dynamics at burnout
	"""
	mdot      = thrust / (isp * g)
	t_burn    = m_prop / mdot
	m_burnout = m_i - m_prop

	def dynamics_boost(t: float, y: Sequence[float]) -> list[float]:
		h, v = y[0], y[1]
		m = m_i - mdot * t

		_, _, rho, a = atm(max(0.0, h))
		f_net = thrust - drag_force(v, diam, rho, a, aero)

		# Held on the pad until the thrust lifts the rocket
		if h <= 0.0 and f_net / m <= g:
			return [max(0.0, v), 0.0]
		return [v, (f_net / m) - g]

	def dynamics_coast(t: float, y: Sequence[float]) -> list[float]:
		h, v = y[0], y[1]
		_, _, rho, a = atm(max(0.0, h))
		return [v, -drag_force(v, diam, rho, a, aero) / m_burnout - g]

	# Apogee is where the climb speed falls through zero
	def apogee_event(t: float, y: Sequence[float]) -> float:
		return y[1]

	setattr(apogee_event, "terminal", True)
	setattr(apogee_event, "direction", -1)

	sol_boost = solve_ivp(
		dynamics_boost, t_span=(0.0, t_burn), y0=[0.0, 0.0],
		method="RK45", rtol=RTOL, atol=ATOL,
	)

	sol_coast = solve_ivp(
		dynamics_coast, t_span=(0.0, COAST_SPAN_S), y0=sol_boost.y[:, -1],
		method="RK45", rtol=RTOL, atol=ATOL, events=apogee_event,
	)

	return t_burn, float(sol_coast.y[0][-1])
#endregion

class TrajectoryComponent(ExplicitComponent):
	"""
	Vertical 1D flight with drag, at constant thrust and Isp

	The ODE integration is real-valued only, so the apogee partials are
	finite differences. The burn time partials are exact
	"""

	def initialize(self):
		# Atmosphere model
		self.options.declare("atm",  types=BEARS_Atm)
		# Drag coefficient table
		self.options.declare("aero", types=AerodynamicsConfig)

	def setup(self):
		# Constant thrust [N]
		self.add_input("thrust",          val=1000.0, units="N")
		# Constant Isp [s]
		self.add_input("isp",             val=200.0,  units="s")
		# Liftoff mass [kg]
		self.add_input("initial_mass",    val=15.0,   units="kg")
		# Burned propellant mass [kg]
		self.add_input("propellant_mass", val=5.0,    units="kg")
		# Airframe diameter for the drag area [m]
		self.add_input("diameter",        val=0.125,  units="m")

		# Peak altitude of the 1D flight [m]
		self.add_output("apogee",    val=3000.0, units="m")
		# Engine burn time [s]
		self.add_output("burn_time", val=3.0,    units="s")

	def setup_partials(self):
		self.declare_partials(
			"burn_time", ["thrust", "isp", "propellant_mass"],
		)

		self.declare_partials(
			"apogee",
			["thrust", "isp", "propellant_mass", "initial_mass", "diameter"],
			method="fd",
			step=1e-5,
		)

	def compute_partials(self, inputs, partials):
		thrust = inputs["thrust"][0]
		isp    = inputs["isp"][0]
		m_prop = inputs["propellant_mass"][0]

		# t_burn = m_prop * isp * g / thrust
		partials["burn_time", "propellant_mass"] = isp * g / thrust
		partials["burn_time", "isp"]             = m_prop * g / thrust
		partials["burn_time", "thrust"]          = (
			-m_prop * isp * g / thrust**2
		)

	def compute(self, inputs, outputs):
		burn_time, apogee = ballistic_apogee(
			inputs["thrust"][0],
			inputs["isp"][0],
			inputs["initial_mass"][0],
			inputs["propellant_mass"][0],
			inputs["diameter"][0],
			self.options["atm"],
			self.options["aero"],
		)

		outputs["burn_time"] = burn_time
		outputs["apogee"]    = apogee
