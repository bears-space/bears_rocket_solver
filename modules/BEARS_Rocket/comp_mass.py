#region Imports
from openmdao.api import ExplicitComponent
#endregion

class MassComponent(ExplicitComponent):
	"""
	Mass budget of the rocket

	TODO: preliminary model. The non-propulsion mass scales linearly with the
	      airframe diameter, and the engine mass is a fixed input
	"""

	def setup(self):
		# Outer airframe diameter [m]
		self.add_input("diameter",            val=0.125, units="m")
		# Outer diameter the non-propulsion mass is given at [m]
		self.add_input("ref_diameter",        val=0.125, units="m")
		# Everything except propulsion system, at ref_diameter [kg]
		self.add_input("non_propulsion_mass", val=8.0,   units="kg")
		# Engine hardware without propellant [kg]
		self.add_input("engine_dry_mass",     val=4.0,   units="kg")
		# Empty oxidizer tank [kg]
		self.add_input("ox_tank_mass",        val=2.0,   units="kg")
		# Empty pressurant bottle [kg]
		self.add_input("press_tank_mass",     val=2.0,   units="kg")
		# Burned propellant [kg]
		self.add_input("propellant_mass",     val=10.0,  units="kg")
		# Pressurant gas [kg]
		self.add_input("pressurant_mass",     val=0.5,   units="kg")
		# Burned over loaded propellant [-]
		self.add_input("eta_prop",            val=1.0)

		# Tanks, engine and non-propulsion mass [kg]
		self.add_output("structural_mass",  val=18.0, units="kg")
		# Propellant loaded at liftoff [kg]
		self.add_output("prop_loaded_mass", val=10.0, units="kg")
		# Propellant left unburned at burnout [kg]
		self.add_output("residual_mass",    val=1.0,  units="kg")
		# Mass at burnout, residuals included [kg]
		self.add_output("dry_mass",         val=20.0, units="kg")
		# Mass at liftoff [kg]
		self.add_output("initial_mass",     val=40.0, units="kg")

	def setup_partials(self):
		self.declare_partials("*", "*", method="cs")

	def compute(self, inputs, outputs):
		scale     = inputs["diameter"] / inputs["ref_diameter"]
		m_nonprop = inputs["non_propulsion_mass"] * scale
		m_struct  = (
			inputs["ox_tank_mass"] + inputs["press_tank_mass"]
			+ inputs["engine_dry_mass"] + m_nonprop
		)

		m_prop     = inputs["propellant_mass"]
		m_loaded   = m_prop / inputs["eta_prop"]
		m_residual = m_loaded - m_prop
		m_dry      = m_struct + m_residual

		outputs["structural_mass"]  = m_struct
		outputs["prop_loaded_mass"] = m_loaded
		outputs["residual_mass"]    = m_residual
		outputs["dry_mass"]         = m_dry
		outputs["initial_mass"]     = (
			m_dry + m_prop + inputs["pressurant_mass"]
		)
