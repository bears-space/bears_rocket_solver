# BEARS Rocket Solver — Agent Guidelines

Follow these repository-wide standards across all AI coding agents.
Numbered sections and lists are ordered by importance.

## 1. Core Paradigm and Design Principles

1. **Readability first**
   > Programs must be written for people to read, and only incidentally
   > for machines to execute.
   >
   > -- Harold Abelson

   - Treat code as specification: every component must be understandable from
     its inputs, outputs, and docstrings alone.
   - Add a short inline `#` comment with units on every input variable,
     output variable, record field, and TOML key.

2. **Type-driven and functional style**
   - Favor immutable data records (`@dataclass(frozen=True)`), algebraic union
     types (e.g., `MetalLayer | CompositeLayer`), pure physics functions, and
     structural pattern matching (`match / case`).
   - Make invalid states impossible: every config record must validate its own
     invariants in `__post_init__` using `modules/Config/validation.py`
     helpers (`require`, `require_positive`, `check_keys`, `build`).
   - Build composable extension points (such as pure `CheckFn` functions in
     `modules/BEARS_Rocket/checks.py`) rather than hardcoding checks into
     solver classes.

## 2. Single Source of Truth (`inputs/` and `modules/Config/`)

The code holds no physical or design numbers of its own. Each input file maps
1-to-1 to a loader module under `modules/Config/`:

| Input file | Loader | Contents |
| --- | --- | --- |
| `inputs/constants.toml` | `constants.py` | Universal constants, ISA |
| `inputs/materials.toml` | `materials.py` | Air, walls, gases, propellants |
| `inputs/rocket_inputs.toml` | `rocket.py` | Vehicle, models, optim, sweep |
| `inputs/checks.toml` | `checks.py` | Post-run acceptance limits |

- Read all physical constants (`g0`, `R`, `zero_celsius`, ISA sea-level and
  troposphere constants) from `modules.Config.CONSTANTS`.
- Never import `scipy.constants` or hardcode physical constants in modules.
- Use `from math import pi` for π; keep exact unit conversion factors only
  at input loaders and external backend boundaries (`BEARS_Chem`).
- Reject unknown and missing TOML keys via `check_keys` so typos fail fast.

## 3. Architecture, Units, and Naming

1. **Package boundaries**
   - Keep pure physics in standalone packages (`BEARS_Atmo`, `BEARS_Chem`,
     `BEARS_Isentropic`, `BEARS_Thermo`, `BEARS_Vessels`).
   - Keep OpenMDAO wrappers in `modules/BEARS_Rocket/` using prefixes
     `comp_*` (components), `group_*` (groups), and `prob_*` (problems).
   - Pass physical geometry as inputs; let components compute the resulting
     performance.
   - Pass all dependencies (`cfg`, `limits`, `atm`, `chem`, walls, gas,
     `press_thermo`, `aero`, densities) explicitly as constructor arguments or
     required OpenMDAO `options`. Do not add hidden defaults or globals.

2. **Units**
   - Convert engineering units (`bar`, `deg`, `degC`, `g/cm^3`, `MPa`,
     `kj/mol`) at config load or `IndepVarComp` interfaces (`DesignVars`).
   - Keep all internal physics and `compute()` methods in base SI units
     (`Pa`, `m`, `kg`, `s`, `K`, `rad`, `J/mol`).
   - Declare `units=...` on every dimensional OpenMDAO variable and let
     OpenMDAO convert across connections.

3. **Naming conventions**
   - Vehicle globals (`DesignVars`): `g_*` (`g_outer_diameter`,
     `g_inner_diameter`, `g_non_propulsion_mass`, `g_engine_dry_mass`,
     `g_target_altitude`, `g_target_thrust`, `g_target_chamber_pressure`).
   - Optimization variables (`OptimizationVars`): `o_*` (`o_propellant_mass`,
     `o_mixture_ratio`, `o_injector_area`, `o_nozzle_throat_area`).
   - Efficiencies (`EfficiencyVars`): `eta_*` (`eta_combustion`,
     `eta_trajectory`, `eta_propellant`, `eta_regression`,
     `eta_nozzle_friction`).
   - Shared propulsion and engine signals: `prop_*`, `engine_*`.
   - Subsystem prefixes: `tank_*`, `press_*`, `injector_*`, `fuel_*`,
     `chem_*`, `nozzle_*`.
   - Avoid cryptic abbreviations; use descriptive names (e.g.,
     `tank_wall_thickness`, `tank_dry_mass`).

4. **Modular physics backends**
   - Select swappable backends via `[models]` in `inputs/rocket_inputs.toml`
     using `match / case` (`"auto"` picks the preferred installed library and
     falls back cleanly).

## 4. OpenMDAO and Complex-Step (`method="cs"`) Rules

- Prefer `method="cs"` for analytic components. Reserve `method="fd"` for
  real-valued external solvers (NASA CEA, RocketCEA, CoolProp, `solve_ivp`).
- Never cast component inputs with `float()` inside complex-step components.
- Never call `np.radians` or `np.degrees` on OpenMDAO inputs; declare
  `units="deg"` / `units="rad"` or multiply by `pi / 180.0`.
- Guard real-valued clamps, branches, and signs using `np.iscomplexobj(...)`
  or `np.real(...)` so imaginary parts pass through cleanly.
- For scalar root-finding helpers used under complex step (e.g.,
  `BEARS_Isentropic.supersonic_mach_from_area_ratio`), solve the real root and
  propagate the imaginary part with one analytic Newton step.
- Declare all design variables, constraints, and objectives before calling
  `prob.setup()`.
- Use explicit `self.connect(...)` calls for internal peer feedback cycles
  (such as the chamber pressure loop in `HybridEngineGroup`).

## 5. Code Style and Formatting

- Use **tabs** for indentation and **spaces** for vertical alignment of
  assignments, tuples, and argument lists (tab width = 4 spaces).
- Keep lines within 80 characters unless vertical alignment or inline
  variable comments clearly improve readability.
- Use `#region` and `#endregion` comment blocks for logical section folding
  in Python files.
- Indent and align Markdown and Org files with spaces; code blocks inside them
  follow their target language rules.

## 6. Documentation and Text Standards

- Write comments, docstrings, documentation, and explanations in ASD-STE100
  Simplified Technical English style: active voice, short sentences,
  unambiguous syntax, and one concept per sentence.
- Mark any unvalidated model, curve, or placeholder value with a `TODO` comment
  explaining the limitation.

## 7. Workflow, Verification, and Repository Hygiene

1. **Incremental, reviewable changes**
   - Discuss the architecture and explain the proposed approach before
     implementing large changes.
   - Break large refactors into small, logically grouped steps that keep the
     solver functional after every step.
   - Respect the user's review preference: when a contributor requests manual
     diff review, write small sequential diffs (under 80 lines each) in an
     untracked scratch directory instead of editing tracked files directly.

2. **Scripting and testing**
   - Run scripts with the project virtual environment (`env/bin/python` on
     Linux/macOS, `env\Scripts\python.exe` on Windows).
   - Encapsulate multi-step validation or shell logic in standalone `.py`
     files; never wrap Python code inside inline Bash strings.
   - Always route RocketCEA scratch files into a working directory via
     `BEARS_Chem.set_work_dir("work/RocketCEA")` (or a temporary folder) so
     `*_out` directories never pollute the repository root.
   - Validate code changes by running `python solver.py` (and
     `python solver.py --sweep` when geometry, mass, or drag change) and
     verifying that `prob.verify()` passes without errors.

3. **Repository hygiene**
   - Keep temporary scratch files, prototypes, and agent working directories
     (`.gemini/`, `.claude/`) untracked; never commit them.
   - Update `AI_DISCLOSURE.md` when introducing a new AI model or provider.
