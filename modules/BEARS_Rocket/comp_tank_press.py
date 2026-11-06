# region Imports
import numpy as np

from math       import pi
from .comp_tank import TankComponent

from ..BEARS_Materials import Gas, NITROGEN
# endregion

class PressurantTankComponent(TankComponent):

	def initialize(self):
		super().initialize()
		self.options.declare("gas",         default=NITROGEN, types=Gas)

		# Alternative options for passing gas parameters
		self.options.declare("r_gas",       default=296.8,    types=float)
		self.options.declare("gamma_gas",   default=1.40,     types=float)
		self.options.declare("t_ambient_k", default=303.15,   types=float)

		# * Compressibility factor
		self.options.declare("z_factor",    default=1.15,     types=float)

		# * Saturation (vapor) pressure of the liquid oxidizer
		# Used for pad gas sizing (Dalton's law)
		self.options.declare("p_sat",       default=57.5e5,   types=float)

	def setup_fluid_inputs(self):
		self.add_input("v_ox_displace",  val=0.01, units="m**3")
		self.add_input("p_ox",           val=70e5, units="Pa")

		# Regulator pressure margin
		self.add_input("p_reg_margin",   val=20e5, units="Pa")
		self.add_input("ox_ullage_frac", val=0.10)

	def setup(self):
		super().setup()

		# Thermodynamic outputs
		self.add_output("m_press",     val=1.2,   units="kg")
		self.add_output("rho_press",   val=344.0, units="kg/m**3")
		self.add_output("m_pad",       val=0.01,  units="kg")
		self.add_output("m_burn",      val=0.30,  units="kg")
		self.add_output("f_delivered", val=0.43)

	def compute_thermo(self, inputs):
		v_ox     = inputs["v_ox_displace"][0]
		p_ox     = inputs["p_ox"][0]
		p_margin = inputs["p_reg_margin"][0]
		p_bottle = inputs["p_tank_max"][0]
		uf       = inputs["ox_ullage_frac"][0]

		t0    = self.options["t_ambient_k"]
		gas   = self.options["gas"]
		r_gas = gas.r_specific if gas else self.options["r_gas"]
		gamma = gas.gamma      if gas else self.options["gamma_gas"]
		z     = gas.z_factor   if gas else self.options["z_factor"]
		p_sat = self.options["p_sat"]

		# 1. Pre-pressurization gas pad
		v_u0     = uf * v_ox
		diff_pad = p_ox - p_sat
		p_pad    = diff_pad if np.iscomplexobj(diff_pad) else max(0.0, diff_pad)
		m_pad    = p_pad * v_u0 / (r_gas * t0)

		# 2. Isentropic bottle discharge
		p_end   = p_ox + p_margin
		p_ratio = p_end / p_bottle
		f_del   = 1.0 - (p_ratio)**(1.0 / gamma)
		t_mean  = (
			(t0 / gamma) * (1.0 - p_ratio) / (1.0 - p_ratio**(1.0 / gamma))
		)

		# 3. Burn mass (ullage energy balance) & total delivered + 10%
		m_burn    = (p_ox * v_ox) / (r_gas * t_mean)
		m_press   = 1.10 * (m_burn + m_pad) / f_del
		rho_press = p_bottle / (z * r_gas * t0)

		return m_press, rho_press, m_pad, m_burn, f_del

	def get_fluid_density(self, inputs):
		_, rho_press, _, _, _ = self.compute_thermo(inputs)
		return rho_press

	def get_fluid_mass(self, inputs):
		m_press, _, _, _, _ = self.compute_thermo(inputs)
		return m_press

	def get_ullage_frac(self, inputs):
		return 0.0

	def compute(self, inputs, outputs):
		m_pr, rho_pr, m_pad, m_burn, f_del = self.compute_thermo(inputs)

		outputs["m_press"]     = m_pr
		outputs["rho_press"]   = rho_pr
		outputs["m_pad"]       = m_pad
		outputs["m_burn"]      = m_burn
		outputs["f_delivered"] = f_del

		super().compute(inputs, outputs)

