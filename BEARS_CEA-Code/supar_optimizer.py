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
	formula={"C": 25.0, "H": 52.0}
)

abs = cea.Reactant(
	name="ABS",
	formula={"C": 8, "H": 8, "C":4, "H":6, "C":3, "H":3, "N": 1}
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
	of_ratio = data["of_ratio"]

pc = 30 # Tank Pressure: 60 bar
pi_p = [30] # Pressure Ratio
subar = [1.58] # Subsonic area ratio
supar = 4.0 # Supersonic area ratio Base Value | must be 3 or greater!

# Program
reac = cea.Mixture(reac_names)
prod = cea.Mixture(reac_names, products_from_reactants=True)
solver = cea.RocketSolver(prod, reactants=reac)
solution = cea.RocketSolution(solver)
weights = reac.of_ratio_to_weights(oxidant_weights, fuel_weights, of_ratio)
hc = reac.calc_property(cea.ENTHALPY, weights, T_reactant)/cea.R

solver.solve(
	solution,
	weights,
	pc,
	pi_p,
	subar=subar,
	supar=supar,
	hc=hc,
	iac=True)

# Solution Print
Cf = solution.coefficient_of_thrust
Isp = solution.Isp[4]
Isp_vac = solution.Isp_vacuum

#optimizer-parameter

deviationValue = 1 # Basis-Schrittlänge für den Bereich um den Basis-Wert

# Anzahl der zu optimierenden Nachkommastellen von "supar". 1 heißt also, dass
# alles bis zur ersten Stelle nach dem Komma optimiert wird
optimizedDigits_supar = 4

optimizedSupar = supar

# Funktion zur Optimierung des supar, um den maximalen Isp in Abhängigkeit davon
# zu erhalten.
def suparOptimizer(
	BaseSupar,
	BaseISP,
	solver,
	deviationValue,
	depth = 0
) -> tuple:
	def solve_for_supar(supar_value):
		solver.solve(
			solution,
			weights,
			pc,
			pi_p,
			subar=subar,
			supar=supar_value,
			hc=hc,
			iac=True)

		return solution.Isp[4]

	candidates = [
		(BaseSupar - 2 * deviationValue, solve_for_supar(BaseSupar - 2 * deviationValue)),
		(BaseSupar - deviationValue, solve_for_supar(BaseSupar - deviationValue)),
		(BaseSupar + deviationValue, solve_for_supar(BaseSupar + deviationValue)),
		(BaseSupar + 2 * deviationValue, solve_for_supar(BaseSupar + 2 * deviationValue)),
	]

	better_candidates = [
		(supar_value, isp_values)
		for supar_value, isp_values in candidates
		if isp_values > BaseISP
	]

	if not better_candidates:
		return (BaseSupar, BaseISP)

	best_supar, best_isp = max(
		better_candidates,
		key=lambda pair: pair[1]
	)

	if(depth < 50):
		print(depth)

		# massives performance-Problem: gesamte Berechnung braucht ~2sek
		return suparOptimizer(best_supar, best_isp, solver, deviationValue/10, depth + 1)
	else:
		return (BaseSupar, BaseISP)

print("Base-Werte")
print(f"Supar: {supar}")
print(f"Isp: {Isp} m/s")

print("Zwischenwerte:")
for i in range(optimizedDigits_supar+1):
	deviationValue = 10**(-i)
	optimizedSupar, optimizedISP = suparOptimizer(
		optimizedSupar, Isp, solver, deviationValue)

	print("---------------------------------------------")
	print(f"Supar: {round(optimizedSupar, i)}")
	print(f"Isp: {optimizedISP} m/s")
	if(i == optimizedDigits_supar):
		print("---------------------------------------------")
		print("---------------------------------------------")
		print(f"Optimierter Wert")

		# hier wird nur gerundet, um den foating-point errors entgegenzuwirken
		print(f"Supar: {round(optimizedSupar, optimizedDigits_supar)}")

		print(f"Isp: {optimizedISP} m/s")

# plan ist, die Rundung später rauszunehmen und mit den exakten Werten zu rechnen
with open("cea_values.json", "r") as retrieved:
	data = json.load(retrieved)
	data["supar"] = optimizedSupar
	with open("cea_values.json", "w") as updated:
		json.dump(data, updated, indent=4)
