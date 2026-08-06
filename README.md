# TODOs

In descending order of importance:

- [ ] MDAO class structure

  - [x] Basic setup

  - [ ] Fix trajectory calculator and unrealistic optimization outputs

  - [ ] Refine the propulsion class/component to include subgroups within the
        propulsion assembly

  - [ ] Aerodynamics component

  - [ ] Implement an MDAO `Problem` class that abstracts optimization problems

- [ ] Figure out the correct chemistry of CEA reactants, specifically reactant
      temperatures and enthalpies of formation

- [ ] Move optimization options and inputs from `solver.py` to JSON files in
      `inputs/`

- [ ] Fix RocketCEA's garbage folders (see [note](#rocketcea-note))

- [ ] Move to a JSON5 parsing library to allow for C++-style comments in inputs
      files

# BEARS Rocket Solver

This program aims to implement highly general multi-dimensional
multi-disciplinary optimization for the whole rocket assembly

## Design principles and contributions

> Programs must be written for people to read, and only incidentally for
> machines to execute
>
> -- Harold Abelson

This program aims for generality, and general programs must be understandable to
be reusable. The hope of organizing the code into MDAO class structure is that
each layer of assembly may be understood from its inputs and outputs, with one
central, clearly defined function mapping one to the other

When documenting Python code, please use the
[Sphinx documentation format](https://sphinx-rtd-tutorial.readthedocs.io/en/latest/docstrings.html)

When writing Markdown documentation, please use the
[GitHub-Flavored Markdown](https://github.github.com/gfm/)
spec

## Code structure

`solver.py`: Main problem setup and optimization script that loads modules from
`packages/`

`inputs/`: The inputs directory. The end goal of the project is to have this
directory be the input interface, with the entire solver program reading only
from JSON files in this directory without having to modify the `solver.py`
script itself

`packages/`: This directory contains the components for the central `solver.py`
script, organized into
[Python packages](https://pythonpackaging.info/02-Package-Structure.html#Package-layout)

`packages/BEARS_Chem/`: The [CEA](#cea) parser module. Contains functions to
read the reactant data from input JSONs and parse it into a CEA object to be
passed to the propulsion subsystem

`packages/BEARS_Rocket/`: Classes for the [OpenMDAO](#openmdao) rocket assembly
structure. Each file defines one component class, and each file is prefixed with
the component type it defines: `group_`, `comp_`, etc

## MDAO class structure

The current class structure of the rocket assembly looks as follows:

| Class | OpenMDAO Component type | Inputs | Outputs | Comments |
| ----- | ----------------------- | ------ | ------- | -------- |
| RocketGroup  | Group  | -  | - | The top-level rocket assembly group. This is where the inputs and outputs of individual subsystems are connected together |
| TrajectoryComponent | ExplicitComponent | `thrust`<br>`isp`<br>`initial_mass`<br>`dry_mass` | `apogee` | The trajectory calculator component. In the future, this component may also contain the encoding of the flight plan for >1D trajectories |
| MassComponent | ExplicitComponent | `payload_mass`<br>`propellant_mass`<br>`structural_coefficient` | `initial_mass`<br>`dry_mass` | Mass profile of the rocket. Preliminary and will probably be superseded by better calculation methods |
| ChemComponent | ExplicitComponent | `chamber_pressure`<br>`mixture_ratio`<br>`expansion_ratio` | `cstar`<br>`isp`<br>`thrust` | Propulsion chemistry subsystem using the CEA solver. This is to be broken up into further subassemblies: nozzle, fuel stack, tank(, injector?) |

This structure is in very early development and is subject to drastic
change. This table will evolve as sub-assemblies are refined

![rocket-structure](figures/dataflow.png "Data flow diagram of the current class structure")

## Setting up the environment

Install the following required Python packages:

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

# for Bash shells; use appropriate activation method on your system
source env/bin/activate

pip install rocketcea openmdao pydot graphviz
```

<a name="rocketcea-note"></a>
**Note:** When the program is run, RocketCEA will create some temporary garbage
folders like `solver_out` in the project directory and `RocketCEA` in your home
directory. TODO figure out how to instruct RocketCEA to put it in an
appropriate manageable location

## Package notes

### OpenMDAO

[OpenMDAO](https://openmdao.org/) (Muldi-Disciplinary Analysis and
Optimization) is the multidisciplinary optimizer that ties the whole solver
program together. OpenMDAO works by organizing large calculations into groups
and subsystems with corresponding Python classes

### RocketCEA

[CEA](https://www.nasa.gov/glenn/research/chemical-equilibrium-with-applications/)
is NASA's isentropic chemistry solver written primarily in Fortran. We use CEA
Python wrappers in this program for computing the propulsion chemistry

We use
[RocketCEA](https://rocketcea.readthedocs.io/en/latest/index.html)
instead of the plain
[CEA Python interface](https://nasa.github.io/cea/interfaces/python_api.html)
used in a previous version of the program because this new package is designed
specifically for rocketry development and is somewhat more convenient

CEA doesn't understand the full chemistry of polymer reactants, and polymers
are modelled with a pseudo-species of fixed polymer chain length

ABS properties used in some of the scripts can be found in this table:
[PubChem ABS table](https://pubchem.ncbi.nlm.nih.gov/compound/ACRYLONITRILE-BUTADIENE-STYRENE#section=Computed-Properties)
