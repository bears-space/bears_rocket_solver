#region Imports
import numpy as np

from math         import pi
from openmdao.api import ExplicitComponent

from ..Config        import Wall, clamp_nonneg
from ..BEARS_Vessels import (
	domes_internal_volume,
	domes_length,
	tank_internal_volume,
	size_layers,
	layer_masses,
)
#endregion

class TankComponent(ExplicitComponent):
	"""
	Cylindrical pressure tank closed by isotensoid domes, sized around the
	fluid it stores. The wall layers are sized to the tank pressure

	Subclasses add the inputs of their stored fluid and call `size_tank` with
	its mass, density and ullage fraction
	"""

	def initialize(self):
		self.options.declare("wall", types=Wall)  # Wall layup, from the inside out

	def setup(self):
		n_layers = len(self.options["wall"].layers)

		self.add_input("p_tank_max",    val=70e5,  units="Pa")  # Maximum tank pressure
		self.add_input("diam_out",      val=0.15,  units="m")   # Outer tank diameter
		self.add_input("safety_factor", val=1.5)                # Burst over maximum pressure [-]
		self.add_input("boss_len_fwd",  val=0.015, units="m")   # Forward boss fitting length
		self.add_input("boss_len_aft",  val=0.015, units="m")   # Aft boss fitting length

		self.add_output("t_layers",   units="m",  shape=n_layers)  # Thickness of each wall layer, inside out
		self.add_output("m_layers",   units="kg", shape=n_layers)  # Mass of each wall layer, inside out
		self.add_output("t_wall",     val=0.002, units="m")        # Total wall thickness
		self.add_output("l_tank",     val=0.5,   units="m")        # Overall length, domes and bosses included
		self.add_output("v_internal", val=0.01,  units="m**3")     # Internal volume
		self.add_output("v_fluid",    val=0.009, units="m**3")     # Volume of the stored fluid
		self.add_output("m_tank_dry", val=2.0,   units="kg")       # Empty tank mass

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def size_tank(self, inputs, outputs, m_fluid, rho_fluid, ullage_frac):
		"""Size the wall and geometry around `m_fluid` [kg] of fluid of density `rho_fluid` [kg/m^3]"""
		wall  = self.options["wall"]
		r_out = inputs["diam_out"][0] / 2.0

		ts     = size_layers(wall, inputs["p_tank_max"][0], r_out, inputs["safety_factor"][0])
		t_wall = sum(ts)
		r_in   = r_out - t_wall

		# The cylinder holds whatever the domes do not, never a negative volume
		v_fluid = m_fluid / rho_fluid
		v_int   = tank_internal_volume(v_fluid, ullage_frac)
		v_cyl   = clamp_nonneg(v_int - domes_internal_volume(r_in))

		l_cyl = v_cyl / (pi * r_in**2)
		l_tot = l_cyl + domes_length(r_in) + inputs["boss_len_fwd"][0] + inputs["boss_len_aft"][0]

		masses = layer_masses(wall, ts, r_in, l_cyl)

		outputs["t_layers"]   = np.asarray(ts)
		outputs["m_layers"]   = np.asarray(masses)
		outputs["t_wall"]     = t_wall
		outputs["l_tank"]     = l_tot
		outputs["v_internal"] = v_int
		outputs["v_fluid"]    = v_fluid
		outputs["m_tank_dry"] = sum(masses)
