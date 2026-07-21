import cea
import json
import numpy as np

"""
Weitere Aufgaben:
- Combustion chamber diameter rausfinden (initial port diameter of the nozzle)
"""

# Inputs
paraffin = cea.Reactant(                                                            
	name="Paraffin",
	formula={"C": 25.0, "H": 52.0},
	# Enthalpie angeben sinnvoll?
	#enthalpy=-681.7,
	#enthalpy_units="kJ/mol",
)

abs = cea.Reactant(
	name="ABS",
	formula={"C": 8, "H": 8, "C":4, "H":6, "C":3, "H":3, "N": 1},      
)

reac_names = [paraffin, abs, "N2O"]                                                     
T_reactant = np.array([298.15, 298.15, 298.15])

fuel_volumes = np.array([0.9, 0.1, 0.0])
oxidant_volumes = np.array([0.0, 0.0, 1.0])

density_parrafin = 0.9  # g/cm^3
density_abs = 1.04  # g/cm^3
density_n2o = 1.2  # g/cm^3

fuel_weights = np.array([
	fuel_volumes[0]*density_parrafin,
	fuel_volumes[1]*density_abs,
	fuel_volumes[2]*density_n2o])

oxidant_weights = np.array([
	oxidant_volumes[0]*density_parrafin,
	oxidant_volumes[1]*density_abs,
	oxidant_volumes[2]*density_n2o])

with open("cea_values.json", "r") as retrieved:
	data = json.load(retrieved)

	# oxidizer/fuel ratio
	of_ratio = data["of_ratio"]

	# Supersonic area ratio
	supar = data["supar"]
    
pc = 30# Tank Pressure: 60 bar
pi_p = [30]# Pressure Ratio
subar = [1.58]# Subsonic area ratio                                                       

# Program
reac = cea.Mixture(reac_names)
prod = cea.Mixture(reac_names, products_from_reactants=True)
solver = cea.RocketSolver(prod, reactants=reac)
solution = cea.RocketSolution(solver)
weights = reac.of_ratio_to_weights(oxidant_weights, fuel_weights, of_ratio)
hc = reac.calc_property(cea.ENTHALPY, weights, T_reactant)/cea.R
solver.solve(solution, weights, pc, pi_p, subar=subar, supar=supar, hc=hc, iac=True)




# Solution Print
num_pts = solution.num_pts
T = solution.T
P = solution.P
rho = solution.density
enthalpy = solution.enthalpy
energy = solution.energy
gibbs = solution.gibbs_energy
entropy = solution.entropy
M_1n = solution.M
MW = solution.MW
cp_eq = solution.cp_eq
cp_fr = solution.cp_fr
cv_eq = solution.cv_eq
cv_fr = solution.cv_fr
Mach = solution.Mach
gamma_s = solution.gamma_s
v_sonic = solution.sonic_velocity
ae_at = solution.ae_at
c_star = solution.c_star
Cf = solution.coefficient_of_thrust
Isp = solution.Isp
Isp_vac = solution.Isp_vacuum

for i in range(num_pts):
    print("")
    print("")

    print("num_pts = ", i)

    print("P, bar         ", end=" ")
    print("{0:10.3f}".format(P[i]))

    print("T, K           ", end=" ")
    print("{0:10.3f}".format(T[i])) 

    print("Density, kg/m^3", end=" ")
    print("{0:10.3f}".format(rho[i]))

    print("H, kJ/kg       ", end=" ")
    print("{0:10.2f}".format(enthalpy[i]))

    print("U, kJ/kg       ", end=" ")
    print("{0:10.2f}".format(energy[i]))

    print("G, kJ/kg       ", end=" ")
    print("{0:10.1f}".format(gibbs[i]))

    print("S, kJ/kg-K     ", end=" ")
    print("{0:10.3f}".format(entropy[i]))

    print("M, (1/n)       ", end=" ")
    print("{0:10.3f}".format(M_1n[i]))

    print("MW             ", end=" ")
    print("{0:10.3f}".format(MW[i]))

    print("Cp_eq, kJ/kg-K ", end=" ")
    print("{0:10.3f}".format(cp_eq[i])) 

    print("Cp_fr, kJ/kg-K ", end=" ")
    print("{0:10.3f}".format(cp_fr[i])) 

    print("Cv_eq, kJ/kg-K ", end=" ")
    print("{0:10.3f}".format(cv_eq[i]))

    print("Cv_fr, kJ/kg-K ", end=" ")
    print("{0:10.3f}".format(cv_fr[i]))

    print("Gamma_s        ", end=" ")
    print("{0:10.3f}".format(gamma_s[i]))

    print("Son. vel., m/s ", end=" ")
    print("{0:10.2f}".format(v_sonic[i]))

    print("Mach           ", end=" ")
    print("{0:10.3f}".format(Mach[i]))

    print()
    print("PERFORMANCE PARAMETERS")
    print()

    print("Ae/At          ", end=" ")
    print("{0:10.3f}".format(ae_at[i]))

    print("C*, m/s        ", end=" ")
    print("{0:10.2f}".format(c_star[i]))

    print("Cf             ", end=" ")
    print("{0:10.4f}".format(Cf[i]))

    print("Isp, vac., m/s ", end=" ")
    print("{0:10.3f}".format(Isp_vac[i]))

    print("Isp, m/s       ", end=" ")
    print("{0:10.3f}".format(Isp[i]))

    print("")
    print("")

print()
print("MOLE FRACTIONS")
print("")
trace_species = []
for prod in solution.mole_fractions:
    if np.any(solution.mole_fractions[prod] > 5e-6):
        print("{0:15s}".format(prod), end=" ")
        for j in range(len(solution.mole_fractions[prod])):
            if j < len(solution.mole_fractions[prod])-1:
                print("{0:10.5g}".format(solution.mole_fractions[prod][j]), end=" ")
            else:
                print("{0:10.5g}".format(solution.mole_fractions[prod][j]))
    else:
        trace_species.append(prod)

print()
print("TRACE SPECIES:")
max_cols = 8
nrows = (len(trace_species) + max_cols - 1) // max_cols
for i in range(nrows):
    print(" ".join("{0:15s}".format(trace_species[j]) for j in range(i * max_cols, min((i + 1) * max_cols, len(trace_species)))))
