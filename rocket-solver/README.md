# Code structure

- `solver.py`: Main problem setup and optimization script

- `inputs/`: The inputs directory

- `packages/BEARS_Chem/`: The [CEA](#cea) parser module. Contains functions to
  read the reactant data from input JSONs and parse it into a CEA object to be
  passed to the propulsion subsystem

- `packages/BEARS_Rocket/`: The [OpenMDAO](#openmdao) rocket assembly structure.

# Packages

## Required packages

``` bash
openmdao
rocketcea

# For structure visualization
pydot
graphviz
```

Ininitalize a Python virtual environment:

``` bash
python -m venv env
source env/bin/activate
pip install openmdao rocketcea
```

Or execute the `recreate-env` Bash script

## Package notes

### OpenMDAO

[OpenMDAO](https://openmdao.org/) (Open Muldi-Disciplinary Analysis and
Optimization) is the multidisciplinary optimizer that will tie the whole solver
program together. OpenMDAO works by organizing large calculations into groups
and subsystems with corresponding Python classes

| Module              | Component type    | Inputs | Outputs        |
| ------------------- | ----------------- | ------ | -------------- |
| RocketGroup         | Group             | -      | -              |
| TrajectoryComponent | ExplicitComponent | `thrust`<br>`isp`<br>`initial_mass`<br>`dry_mass` | `apogee` |
| MassComponent       | ExplicitComponent | `payload_mass`<br>`propellant_mass`<br>`structural_coefficient` | `initial_mass`<br>`dry_mass` |
| ChemComponent       | ExplicitComponent | `chamber_pressure`<br>`mixture_ratio`<br>`expansion_ratio` | `cstar`<br>`isp`<br>`thrust` |

### CEA

[CEA](https://www.nasa.gov/glenn/research/chemical-equilibrium-with-applications/)
is NASA's isentropic chemistry solver that will be used for chemical
computations

We use [RocketCEA](https://rocketcea.readthedocs.io/en/latest/index.html)
instead of the plain
[CEA Python interface](https://nasa.github.io/cea/interfaces/python_api.html)
because that package is intended specifically for rocketry development

CEA doesn't understand the full chemistry of polymer reactants, and polymers
are modelled with a pseudo-species of fixed polymer chain length

# Theory

## Chemical data

[ABS properties](https://pubchem.ncbi.nlm.nih.gov/compound/ACRYLONITRILE-BUTADIENE-STYRENE#section=Computed-Properties)
