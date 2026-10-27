# region Imports
import numpy as np

from numpy.typing      import NDArray
from scipy.integrate   import solve_ivp
from scipy.interpolate import interp1d
from scipy.constants   import g
from openmdao.api      import ExplicitComponent

from ..BEARS_Atmo import BEARS_Atm
# endregion

# region Ballistic functions
def F_d(v: float, diam: float, rho: float, a: float) -> float:
	"""Drag force calculator"""

	area = np.pi * (diam / 2.0)**2.0
	mach = abs(v) / a

	# TODO: Better-founded C_d model, currently AI-generated
	if mach < 0.8:
		# Subsonic: skin friction and base drag
		cd = 0.40
	elif mach < 1.2:
		# Transonic: drag increase due to shock wave
		# Linear interpolation (mach = 0.8, cd = 0.4) -- (mach = 1.2, cd = 0.8)
		cd = 0.4 + (mach - 0.8) * ( (0.8 - 0.4) / (1.2 - 0.8) )
	elif mach < 2.0:
		# Supersonic: drag decreases as Mach number increases
		# Linear interpolation (1.2, 0.8) -- (2.0, 0.6)
		cd = 0.4 + (mach - 1.2) * ( (0.8 - 0.6) / (2.0 - 1.2) )
	else:
		# High supersonic
		cd = 0.6

	drag = 0.5 * rho * v**2 * cd * area
	return drag

def ballistic_apogee(
	thrust: float,
	isp: float,
	m_i: float,
	m_dry: float,
	diam: float,
	atm: BEARS_Atm
) -> tuple[float, float]:
	"""
	Simple ballistic apogee calculator.

	We use a two-step boost+coast process with separate dynamics and integrators
	in order to avoid a sharp discontinuity in the integrator.
	"""
	mdot = thrust / (isp * g)
	t_burn = (m_i - m_dry) / mdot

	def dynamics_boost(t, y):
		h, v = y
		m = m_i - mdot * t

		_, _, rho, a = atm(h)

		dh_dt = v
		dv_dt = (thrust - F_d(v, diam, rho, a)) / m - g
		return [dh_dt, dv_dt]

	def dynamics_coast(t, y):
		h, v = y

		_, _, rho, a = atm(h)

		dh_dt = v
		dv_dt = -F_d(v, diam, rho, a) / m_dry - g
		return [dh_dt, dv_dt]

	# A SciPy integration event that captures the moment when velocity reaches 0
	def apogee_event(t, y): return y[1]
	apogee_event.terminal = True
	apogee_event.direction = -1

	# Integration steps
	sol_boost = solve_ivp(
		dynamics_boost,
		t_span=(0.0, t_burn),
		y0=[0.0, 0.0],
		method="RK45",
		rtol=1e-7,
		atol=1e-9,
	)

	h_burnout = sol_boost.y[0][-1]
	v_burnout = sol_boost.y[1][-1]

	sol_coast = solve_ivp(
		dynamics_coast,
		t_span=(0, 1000),
		y0=[h_burnout, v_burnout],
		method="RK45",
		rtol=1e-7,
		atol=1e-9,
		events=apogee_event,
	)

	apogee = sol_coast.y[0][-1]
	return t_burn, apogee

def ballistic_apogee_var(
	time_steps: NDArray,
	thrust_profile: NDArray,
	isp_profile: NDArray,
	m_i: float,
	m_dry: float,
) -> float:
	"""
	A more complicated ballistic function that calculates the trajectory apogee
	based on a variable thrust and Isp profile, passed in as an array of
	measured values relative to the time series
	"""

	f_thrust = interp1d(
		time_steps, thrust_profile, bounds_error=False, fill_value=0.0
	)

	f_isp = interp1d(
		time_steps, isp_profile, bounds_error=False, fill_value=0.0
	)

	def dynamics(t, y):
		h, v, m = y

		thrust = f_thrust(t)
		isp = f_isp(t)

		if isp > 0 and m > m_dry:
			mdot = thrust / (isp * g)
		else:
			mdot = 0
			thrust = 0.0

		dh_dt = v
		dv_dt = (thrust / m) - g
		dm_dt = -mdot

		return [dh_dt, dv_dt, dm_dt]

	def apogee_event(t, y): return y[1]
	apogee_event.terminal = True
	apogee_event.direction = -1

	sol = solve_ivp(
		dynamics,
		t_span=(0, 1000),
		y0=[0.0, 0.0, m_i],
		method="RK45",
		rtol=1e-7,
		atol=1e-9,
		events=apogee_event,
	)

	apogee = sol.y[0][-1]
	return apogee
# endregion

class TrajectoryComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("atm", types=BEARS_Atm)

	def setup(self):
		# t = np.linspace(0, 10, 1000)
		# thrust_profile = np.where((t < 5.0), 1200, 0)
		# isp_profile = np.where((t < 5.0), 180, 0)

		# self.add_input('time_steps',     val=t,              units='s')
		# self.add_input('thrust_profile', val=thrust_profile, units='N')
		# self.add_input('isp_profile',    val=isp_profile,    units='s')

		# Propulsion profile
		self.add_input("thrust", val=1000.0, units="N")
		self.add_input("isp",    val=200.0,  units="s")

		# Rocket parameters
		self.add_input("initial_mass", val=15.0, units="kg")
		self.add_input("dry_mass",     val=5.0,  units="kg")
		self.add_input("diameter",     val=0.5,  units="m")

		self.add_output("apogee",    val=3000.0, units="m")
		self.add_output("burn_time", val=3.0,    units="s")

	def setup_partials(self):
		self.declare_partials(
			"burn_time", ["thrust", "isp", "initial_mass", "dry_mass"]
		)

		self.declare_partials(
			"apogee",
			["thrust", "isp", "initial_mass", "dry_mass", "diameter"],
			method="fd",
			step=1e-5,
		)

	def compute_partials(self, inputs, partials):
		thrust = inputs["thrust"][0]
		isp    = inputs["isp"][0]
		m_i    = inputs["initial_mass"][0]
		m_dry  = inputs["dry_mass"][0]

		# Provide exact partial derivatives:
		#
		#   t_burn = ( (m_i - m_dry) * isp * g ) / thrust
		#

		partials["burn_time", "initial_mass"] =  (isp * g) / thrust
		partials["burn_time", "dry_mass"]     = -(isp * g) / thrust
		partials["burn_time", "isp"]          =  (m_i - m_dry) * g / thrust
		partials["burn_time", "thrust"]       = -(
			(m_i - m_dry) * isp * g
		) / (thrust**2)

	def compute(self, inputs, outputs):
		atm = self.options["atm"]

		thrust = inputs["thrust"][0]
		isp    = inputs["isp"][0]
		m_i    = inputs["initial_mass"][0]
		m_dry  = inputs["dry_mass"][0]
		diam   = inputs["diameter"][0]

		burn_time, apogee = ballistic_apogee(thrust, isp, m_i, m_dry, diam, atm)

		outputs["burn_time"] = burn_time
		outputs["apogee"]    = apogee
