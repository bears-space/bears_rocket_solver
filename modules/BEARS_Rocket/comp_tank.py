# region Imports
import numpy as np

from math         import pi
from openmdao.api import ExplicitComponent

from ..BEARS_Materials import AL_6061_T6
from ..BEARS_Materials import Layer, LayeredWall
# endregion

class TankComponent(ExplicitComponent):

	def initialize(self):
		self.options.declare(
			"wall_material",
			default=None,
			types=(LayeredWall, type(None)),
		)

	def setup(self):
		wall = self.options["wall_material"]
		n_layers = len(wall.layers) if wall else 1

		self.add_input("m_fluid",       val=10.0,   units="kg")
		self.add_input("rho_fluid",     val=1000.0, units="kg/m**3")

		self.add_input("p_tank_max",    val=70e5,   units="Pa")
		self.add_input("diam_out",      val=0.15,   units="m")
		self.add_input("ullage_frac",   val=0.1)

		self.add_input("safety_factor", val=1.5)
		self.add_input("sigma_y",       val=276e6,  units="Pa")
		self.add_input("rho_wall",      val=2700.0, units="kg/m**3")

		self.add_output("t_wall",       val=0.002,  units="m")
		self.add_output("t_liner",      val=0.001,  units="m")
		self.add_output("t_wrap",       val=0.001,  units="m")
		self.add_output("m_liner",      val=1.0,    units="kg")
		self.add_output("m_wrap",       val=1.0,    units="kg")

		self.add_output("t_layers",                 units="m",  shape=n_layers)
		self.add_output("m_layers",                 units="kg", shape=n_layers)

		self.add_output("l_tank",       val=5.0,    units="m")
		self.add_output("v_internal",   val=5.0,    units="m**3")
		self.add_output("v_fluid",      val=4.5,    units="m**3")
		self.add_output("m_tank_dry",   val=2.0,    units="kg")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def get_fluid_mass(self, inputs):
		return inputs["m_fluid"]

	def get_fluid_density(self, inputs):
		return inputs["rho_fluid"]

	def get_ullage_frac(self, inputs):
		return inputs["ullage_frac"]

	def compute(self, inputs, outputs):
		m_fluid = self.get_fluid_mass(inputs)
		rho_f   = self.get_fluid_density(inputs)
		uf      = self.get_ullage_frac(inputs)

		p_max   = inputs["p_tank_max"][0]
		d_out   = inputs["diam_out"][0]
		sigma_y = inputs["sigma_y"][0]
		sf      = inputs["safety_factor"][0]
		rho_w   = inputs["rho_wall"][0]

		# Hoop stress
		# <https://www.engineersedge.com/material_science/hoop-stress.htm>

		wall = self.options["wall_material"]
		if wall is None: wall = LayeredWall(Layer(AL_6061_T6))

		r_out = d_out / 2.0
		ts = wall.size_layers(p_max, r_out, sf)
		t_wall = sum(ts)

		r_in = r_out - t_wall
		d_in = 2.0 * r_in

		# Volumes and lengths
		v_fluid = m_fluid / rho_f
		v_int = v_fluid / (1.0 - uf)
		v_caps = (4.0 / 3.0) * pi * r_in**3 # Hemispherical caps

		diff_v = v_int - v_caps
		if np.iscomplexobj(diff_v):
			v_cyl = diff_v if diff_v.real > 0.0 else 0.0
		else:
			v_cyl = max(0.0, diff_v)

		a_int = pi * r_in**2
		l_cyl = v_cyl / a_int
		l_tot = l_cyl + d_out

		m_dry, masses = wall.compute_masses(ts, r_in, l_cyl)

		outputs["t_layers"]   = np.asarray(ts)
		outputs["m_layers"]   = np.asarray(masses)
		outputs["t_liner"]    = ts[0]
		outputs["t_wrap"]     = ts[1] if len(ts) > 1 else 0.0
		outputs["m_liner"]    = masses[0]
		outputs["m_wrap"]     = masses[1] if len(masses) > 1 else 0.0
		outputs["t_wall"]     = t_wall

		outputs["l_tank"]     = l_tot
		outputs["v_internal"] = v_int
		outputs["v_fluid"]    = v_fluid
		outputs["m_tank_dry"] = m_dry
