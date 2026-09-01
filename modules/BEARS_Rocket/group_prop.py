# region Imports
from openmdao.api      import Group
from rocketcea.cea_obj import CEA_Obj

from .comp_tank import TankComponent
from .comp_cea  import ChemComponent
# endregion

class PropulsionGroup(Group):

	def initialize(self):
		self.options.declare("cea", types=CEA_Obj)

	def setup(self):
		cea = self.options["cea"]

		#region Subsystems
		self.add_subsystem(
			"Tank",
			TankComponent(),
			promotes_inputs=["diam_out", "m_prop_i", "mixture_ratio"],
			promotes_outputs=["m_tank_dry"],
		)

		# Between tank and injector we have a ~30bar pressure loss
		# -> "Plumbing component"
		# TODO: elaborate the plumbing with the rest of the team

		self.add_subsystem(
			"Chemistry",
			ChemComponent(cea=cea),
			promotes_inputs=[
				"chamber_pressure", "mixture_ratio", "expansion_ratio"
			],
			promotes_outputs=["cstar", "isp", "thrust"],
		)
		#endregion

