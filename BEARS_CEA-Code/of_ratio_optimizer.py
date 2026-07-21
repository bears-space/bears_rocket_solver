# -*- coding: utf-8 -*-
"""
Created on Thu Jun 11 22:20:05 2026

@author: Robert

im Folgenden wird die ungefähre Funktionsweisre der optimizer erklärt:
Basiswert geht rein -> Basis-Isp 
Werte um Basiswert -> Isp-Werte um Basis
ISps werden abgleichen
wenn einer der Werte um Base-Isp > Base-Isp -> wird zu neuem Basiswert

Das wird wiederholt, bis die "Spitze" gefunden wurde, woraufhin der Bereich um
Faktor 10 verkleinert wird Das wird so oft wiederholt, wie man zu optimierende
Nachkommastellen (optimizedDigits_X) angegeben hat

Anders als ein Line-Sweep ist diese Methode jedoch anfällig für lokale Maxima,
was ich durch eine relativ große Area versucht habe, zu minimieren
"""

import json
import cea
import numpy as np


# Inputs
paraffin = cea.Reactant(                                                            
	name="Paraffin",
	formula={"C": 25.0, "H": 52.0},                                                
)

abs = cea.Reactant(
	name="ABS",
	formula={"C": 8, "H": 8, "C":4, "H":6, "C":3, "H":3, "N": 1},      
)

reac_names = [paraffin, abs, "N2O"]                                                  
T_reactant = np.array([298.15, 298.15, 298.15])

fuel_volumes = np.array([0.9, 0.1, 0.0])
oxidant_volumes = np.array([0.0, 0.0, 1.0])

density_parrafin = 0.9 # g/cm^3
density_abs = 1.04 # g/cm^3
density_n2o = 1.2 # g/cm^3

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
	supar = data["supar"] # Supersonic area ratio |siehe optimizer

of_ratio = 5 # Optimizer eingefügt: ~7.6036
pc = 30 # Tank Pressure: 60 bar
pi_p = [30] # Pressure Ratio
subar = [1.58] # Subsonic area ratio | WERT TEMPORAER!!!
supar = 6.469111111108702

# Program
reac = cea.Mixture(reac_names)
prod = cea.Mixture(reac_names, products_from_reactants=True)
solver = cea.RocketSolver(prod, reactants=reac)
solution = cea.RocketSolution(solver)
weights = reac.of_ratio_to_weights(oxidant_weights, fuel_weights, of_ratio)
hc = reac.calc_property(cea.ENTHALPY, weights, T_reactant)/cea.R
solver.solve(solution, weights, pc, pi_p, subar=subar, supar=supar, hc=hc, iac=True)

# Solution Print
Cf = solution.coefficient_of_thrust
Isp = solution.Isp[4]
Isp_vac = solution.Isp_vacuum

#optimizer-parameter

# Basis-Schrittlänge für den Bereich um den Basis-Wert
deviationValue = 1

# Anzahl der zu optimierenden Nachkommastellen von "of-ratio". 1 heißt also,
# dass alles bis zur ersten Stelle nach dem Komma optimiert wird
optimizedDigits_of = 4

optimizedOFRatio = of_ratio

# Funktion zur Optimierung des of_ratio, um den maximalen Isp in Abhängigkeit
# davon zu erhalten.
def oFRatioOptimizer(BaseOFRatio, BaseISP, solver, deviationValue) -> tuple:
	def solve_for_of(of_ratio_value):
		weights = reac.of_ratio_to_weights(oxidant_weights, fuel_weights, of_ratio_value)
		hc = reac.calc_property(cea.ENTHALPY, weights, T_reactant) / cea.R
		solver.solve(solution, weights, pc, pi_p, subar=subar, supar=supar, hc=hc, iac=True)
		return solution.Isp[4]

	candidates = [
		(BaseOFRatio - 2 * deviationValue, solve_for_of(BaseOFRatio - 2 * deviationValue)),
		(BaseOFRatio - deviationValue, solve_for_of(BaseOFRatio - deviationValue)),
		(BaseOFRatio + deviationValue, solve_for_of(BaseOFRatio + deviationValue)),
		(BaseOFRatio + 2 * deviationValue, solve_for_of(BaseOFRatio + 2 * deviationValue)),
	]

	better_candidates = [
		(of_ratio_value, isp_value)
		for of_ratio_value, isp_value in candidates
		if isp_value > BaseISP
	]

	if not better_candidates:
		return (BaseOFRatio, BaseISP)

	best_of_ratio, best_isp = max(
		better_candidates,
		key=lambda pair: pair[1]
	)

	return oFRatioOptimizer(best_of_ratio, best_isp, solver, deviationValue)

print("Base-Werte")
print(f"OF-Ratio: {of_ratio}")
print(f"Isp: {Isp} m/s")

print("Zwischenwerte:")
for i in range(optimizedDigits_of+1):
	deviationValue = 10**-(i)
	optimizedOFRatio, optimizedISP = oFRatioOptimizer(optimizedOFRatio, Isp, solver, deviationValue)
	print("---------------------------------------------")
	print(f"OF-Ratio: {round(optimizedOFRatio, i)}")
	print(f"Isp: {optimizedISP} m/s")
	if(i == optimizedDigits_of):
		print("---------------------------------------------")
		print("---------------------------------------------")
		print(f"Optimierter Wert")
		print(f"OF-Ratio: {round(optimizedOFRatio, optimizedDigits_of)}")
		print(f"Isp: {optimizedISP} m/s")

with open("cea_values.json", "r") as retrieved:
	# fuer mehr infosw siehe kommentar in supar-optimizer
	data = json.load(retrieved)
	data["of_ratio"] = optimizedOFRatio
	with open("cea_values.json", "w") as updated:
		json.dump(data, updated, indent=4)
