# region Imports
from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from ..BEARS_Atmo import BEARS_Atm

from .comp_atmo    import AtmoComponent
from .group_rocket import RocketGroup
# endregion

class ModelGroup(Group):
	"""A MDAO group for the whole model"""

	def initialize(self):
		self.options.declare("atm", types=BEARS_Atm)
		self.options.declare("cea", types=CEA_Obj)

	def setup(self):
		atm = self.options["atm"]
		cea = self.options["cea"]

		# region Subsystems
		self.add_subsystem(
			"Atmosphere",
			AtmoComponent(atm=atm),
			promotes_inputs=["altitude"]
		)

		self.add_subsystem(
			"Rocket",
			RocketGroup(cea=cea),
			promotes_inputs=[
				"propellant_mass", "payload_mass", "mixture_ratio"
			],
			promotes_outputs=["burn_time", "apogee"]
		)
		# endregion

		# region Connections
		# endregion
