#region Imports
from math import pi

import numpy as np

from openmdao.api import ExplicitComponent
#endregion

class IgniterComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare("rho_thermite", default=3800.0, types=float)
		self.options.declare("delta_h_rxn",  default=3.97e6, types=float)
		self.options.declare("eta_thermal",  default=0.35,   types=float)
		self.options.declare("k_fuel",       default=0.25,   types=float)
		self.options.declare("rho_fuel",     default=900.0,  types=float)
		self.options.declare("cp_fuel",      default=2100.0, types=float)
		self.options.declare("t_pyro",       default=650.0,  types=float)
		self.options.declare("t_ambient",    default=298.15, types=float)

	def setup(self):
		self.add_input("diam_out",           val=0.05,   units="m")
		self.add_input("fuel_length",        val=0.35,   units="m")
		self.add_input("t_burn_target",      val=1.0,    units="s")
		self.add_input("burn_rate_thermite", val=1.5e-3, units="m/s")
		self.add_input("flame_spread_rate",  val=0.15,   units="m/s")
		self.add_input("max_spread_delay",   val=0.10,   units="s")

		self.add_output("lining_thickness",  val=1.5e-3, units="m")
		self.add_output("diam_in",           val=0.047,  units="m")
		self.add_output("port_blockage",     val=0.12)
		self.add_output("thermite_mass",     val=0.3,    units="kg")
		self.add_output("num_pads",          val=13.0)
		self.add_output("pad_spacing",       val=0.03,   units="m")
		self.add_output("ignition_margin",   val=10.0)

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		d_out,  l_grain = inputs["diam_out"], inputs["fuel_length"]
		t_burn, r_burn  = inputs["t_burn_target"], inputs["burn_rate_thermite"]
		v_spread, tau   = inputs["flame_spread_rate"], inputs["max_spread_delay"]

		rho_th = self.options["rho_thermite"]
		dh_rxn = self.options["delta_h_rxn"]
		eta_th = self.options["eta_thermal"]

		t_lining = r_burn * t_burn
		d_in     = d_out - 2.0 * t_lining
		blockage = 1.0 - (d_in / d_out)**2
		v_lining = pi * (d_out - t_lining) * t_lining * l_grain
		m_th     = rho_th * v_lining

		l_spread = 2.0 * v_spread * tau
		l_val    = np.real(l_grain) if np.iscomplexobj(l_grain) else l_grain
		spr_val  = np.real(l_spread) if np.iscomplexobj(l_spread) else l_spread
		n_pads   = np.ceil(l_val / np.maximum(1e-4, spr_val)) + 1.0
		spacing  = l_grain / np.maximum(1.0, n_pads - 1.0)

		q_del      = eta_th * rho_th * t_lining * dh_rxn
		q_dot      = q_del / t_burn
		k_f, rho_f = self.options["k_fuel"], self.options["rho_fuel"]
		cp_f       = self.options["cp_fuel"]
		dt         = self.options["t_pyro"] - self.options["t_ambient"]
		q_req      = (pi / 4.0) * (k_f * rho_f * cp_f * (dt**2)) / q_dot

		outputs["lining_thickness"] = t_lining
		outputs["diam_in"]          = d_in
		outputs["port_blockage"]    = blockage
		outputs["thermite_mass"]    = m_th
		outputs["num_pads"]         = n_pads
		outputs["pad_spacing"]      = spacing
		outputs["ignition_margin"]  = q_del / q_req
