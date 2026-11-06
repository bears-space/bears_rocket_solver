#region Imports
from dataclasses import dataclass
#endregion

#region Gas record
@dataclass(frozen=True)
class Gas:
	name       : str
	molar_mass : float # [kg/kmol]
	r_specific : float # [J/(kg*K)]
	gamma      : float # Ratio of specific heats (cp / cv)
	z_factor   : float = 1.0 # Real gas compressibility factor

	@classmethod
	def from_config(cls, cfg) -> "Gas":
		return cls(
			name       = cfg.name,
			molar_mass = cfg.molar_mass,
			r_specific = cfg.r_specific,
			gamma      = cfg.gamma,
			z_factor   = cfg.z_factor,
		)
#endregion

#region Standard presets
NITROGEN = Gas(
	name       = "Nitrogen Gas",
	molar_mass = 28.0134,
	r_specific = 296.8,
	gamma      = 1.40,
	z_factor   = 1.15,
)

HELIUM = Gas(
	name       = "Helium Gas",
	molar_mass = 4.0026,
	r_specific = 2077.2,
	gamma      = 1.667,
	z_factor   = 1.05,
)
#endregion
