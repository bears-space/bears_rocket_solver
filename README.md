# BEARS Rocket Solver

Multidisciplinary design optimization of a hybrid (paraffin/ABS + N2O) sounding
rocket, built on [OpenMDAO](https://openmdao.org/). The solver sizes the
propellant load, mixture ratio, injector and nozzle throat so the rocket reaches
its target apogee with the least propellant.

## Design principles

> Programs must be written for people to read, and only incidentally for
> machines to execute.
>
> -- Harold Abelson

1. **Readability first.** Clear code beats clever code. Every component should
   be understandable from its inputs and outputs alone.
2. **One source of truth for data.** The code holds no numbers of its own.
   Physical constants, material properties and design inputs each live in
   exactly one input file (see [Inputs](#inputs)).
3. **SI units inside, declared units at the interface.** Every OpenMDAO
   variable declares its units. Convert only when reading inputs or printing
   results.
4. **One component, one job.** Each `comp_`/`group_` file models one physical
   subsystem. Dependencies such as the chemistry or atmosphere model are passed
   in as options, never reached for as globals.
5. **Make invalid states impossible.** Design your types so that the only
   values the compiler or constructor will accept are valid ones, which moves
   checks out of scattered runtime `if` statements and into the structure of
   the data itself. 
6. **Keep components differentiable.** Partials are computed by complex step,
   so component code must accept complex inputs (no `float()` casts, no
   branching on values without handling the complex case).
7. **Mark placeholders.** Any model or value that is not validated carries a
   `TODO` saying so.
8. **All variables are explained.** Any input variable and output variable
   should have a #comment explaining exactly what it is.

## Running the solver

Requires Python 3.11+. Graph output additionally needs the system
[Graphviz][gvz] install (`dot` on the `PATH`).
[gvz]: https://graphviz.org/

```powershell
python -m venv env
.\env\Scripts\Activate.ps1      # Windows, or
source env/bin/activate         # Linux/Mac
pip install .                   # Install required dependencies
pip install .[verification]     # Optional: MyPy
pip install .[visualization]    # Optional: pydot, GraphViz

python solver.py                # Optimize and write the outputs, or
python solver.py --sweep        # Run an airframe diameter sweep
```

Results are printed to the terminal, all model variables are written to
`outputs/rocket.txt`, and the model graphs to `figures/rocket_*.png`.

## Inputs

| File | Contents |
| ---- | -------- |
| `inputs/rocket_inputs.toml` | Design inputs: targets, airframe diameters, drag curve, tanks with their wall and gas choice, injector, fuel, nozzle, model choices, efficiencies, optimizer start values and bounds, constraint limits, and the diameter sweep |
| `inputs/checks.toml` | Acceptance limits the optimized rocket is checked against after every run |
| `inputs/materials.toml` | Material properties: air, structural materials, tank wall layups, pressurant gases, propellant reactants |
| `inputs/constants.toml` | Physical constants: universal constants, standard atmosphere |

The tanks are structural and use the outer airframe diameter. The engine sits
inside the airframe and has to fit the inner diameter.

## Model

```
RocketLaunchProblem             # Optimizer setup, checks and reporting
└── RocketGroup
    ├── DesignVars, EfficiencyVars, OptimizationVars
    ├── Propulsion
    │   ├── PropSplit           # Propellant mass -> oxidizer and fuel mass
    │   ├── OxidizerTank        # N2O tank wall and length
    │   ├── PressurantTank      # Pressurant tank and blowdown gas mass
    │   └── HybridEngine
    │       ├── Injector        # Oxidizer mass flow from the pressure drop
    │       ├── Fuel            # Regression rate and grain size
    │       ├── NozzleGeometry  # Exit area, expansion ratio, length
    │       ├── Chemistry       # CEA: flame temperature, gamma, ideal Isp
    │       └── Nozzle          # Choked flow, chamber pressure, thrust
    ├── Mass                    # Dry, loaded and liftoff mass
    ├── EngineFit               # Fuel grain fits the airframe bore
    └── Trajectory              # 1D ballistic flight with drag, apogee
```

The optimizer (SLSQP) minimizes the propellant mass by varying the propellant
mass, mixture ratio, injector area and throat area, subject to the target
apogee, thrust and chamber pressure, a minimum injector pressure drop, a
maximum burn time and the grain fitting the bore.

## Code structure

```
solver.py                # Entry point
inputs/                  # Input TOML files
modules/
├── Config/              # Input records, one module per input file,
│                        # each checking its own values
├── BEARS_Rocket/        # OpenMDAO components (comp_*),
│                        # groups (group_*), problems (prob_*)
├── BEARS_Chem/          # Propellant chemistry, CEA and RocketCEA backends
├── BEARS_Atmo/          # Standard atmosphere
├── BEARS_Thermo/        # Pressurant blowdown and isentropic flow
└── BEARS_Vessels/       # Pressure vessel walls, domes and volumes
outputs/                 # Solver output tables
figures/                 # Model graphs
doc/                     # Derivations and reports
```

## Dependencies

- [OpenMDAO][omd]: optimization framework.
  [omd]: https://openmdao.org/
- [CEA][cea]/[RocketCEA][rce]: NASA chemical equilibrium solver for the
  combustion products. Polymer fuels are modelled as pseudo-species of fixed
  chain length ([ABS properties][abs]).
  [cea]: https://nasa.github.io/cea/interfaces/python_api.html
  [rce]: https://rocketcea.readthedocs.io/
  [abs]: https://pubchem.ncbi.nlm.nih.gov/compound/ACRYLONITRILE-BUTADIENE-STYRENE#section=Computed-Properties
- [CoolProp][cpr]: real-gas pressurant properties, with an ideal-gas fallback.
  [cpr]: http://www.coolprop.org/
- [isacalc][isc]: ISA atmosphere, with a built-in standalone fallback.
  [isc]: https://github.com/LukeDeWaal/ISA_Calculator

The backend for each model is chosen under `[models]` in
`inputs/rocket_inputs.toml`.

## Citations and Credit to useful Papers/resources
- [Glenn Resaerch Center][grc]: Isentropic Calculation source
  [grc]: https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/isentrop/
- [NASA CEA Tutorial][cea]: NASA CEA Explanation and Tutorial
  [cea]: https://ntrs.nasa.gov/api/citations/20240016039/downloads/CEA_SciTech_2025_Leader.pdf
