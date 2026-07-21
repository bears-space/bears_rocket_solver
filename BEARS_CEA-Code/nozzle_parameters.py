"""
Created on Thu Jul 10 16:10:00 2026
@author: Robert
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
	of_ratio = data["of_ratio"] # oxidizer/fuel ratio
	supar = data["supar"] # Supersonic area ratio

pc = 30 # Tank Pressure: 60 bar, loss: 30 bar
pi_p = [30] # Pressure Ratio (Chamber/Outside)
subar = [1.58] # Subsonic area ratio

# Program
reac = cea.Mixture(reac_names)
prod = cea.Mixture(reac_names, products_from_reactants=True)
solver = cea.RocketSolver(prod, reactants=reac)
solution = cea.RocketSolution(solver)
weights = reac.of_ratio_to_weights(oxidant_weights, fuel_weights, of_ratio)
hc = reac.calc_property(cea.ENTHALPY, weights, T_reactant)/cea.R

solver.solve(solution, weights, pc, pi_p,
	subar=subar, supar=supar, hc=hc, iac=True)

# Solution Print
Isp = solution.Isp[4]
Isp_vac = solution.Isp_vacuum

# optimizer-parameter
deviationValue = 1
optimizedDigitCount = 1
optimizedlength = 20 # Startwert, solle aber so gewählt werden, dass supar > 1

# throat-relevante Werte
maximum_nozzle_diameter = 12.5 # in cm
angle_of_expansion = 15 # in grad (Expansionswinkel von 15° annehmen)

# H2O und CO2, als ausgestoßene Gase im 1:1-Verhältnis
molecularWeightExhaustGas = (18.015+44.010)/2

targetThrust = 3000 # in N
massFlowRate = targetThrust/Isp

# 8314.46 ist die universelle Gaskonstante
GasConstant = 8314.46/molecularWeightExhaustGas

ChamberTemp = 3000 # in °K, approximation, von paraffin brenn-temp
ChamberPressure = 3 # 30 bar in N/mm^2
HeatRatio = 1.24 # exhaust gas heat ratio

# Hier wird mit den gegebenen Werten berechnet, wie die Nozzle-Parameter
# aussehen müssen, um den gewünschten Schub zu erreichen.

A_th = (massFlowRate * np.sqrt(GasConstant * ChamberTemp)) / (ChamberPressure * np.sqrt(HeatRatio) * np.power(2 / (HeatRatio + 1), (HeatRatio + 1) / (2 * (HeatRatio - 1))))

d_th = np.sqrt((4 * A_th) / np.pi)

A_noz = A_th*supar
d_noz = np.sqrt((4 * A_noz) / np.pi)

l = ((d_noz/2 - d_th/2)*np.sin(np.radians(90-angle_of_expansion)))/np.sin(np.radians(angle_of_expansion))

if(d_noz < maximum_nozzle_diameter*10):
	print("Nozzle-Parameter:")
	print("")
	print(f"Nozzle-länge: {l} mm")
	print("")
	print(f"Throat-Durchmesser: {d_th} mm")
	print(f"Throat-Fläche: {A_th} mm²")
	print("")
	print(f"Nozzle-Durchmesser: {d_noz} mm")
	print(f"Nozzle-Fläche: {A_noz} mm²")
	print("")
	print(f"Supar: {supar}")
	print(f"Target thrust: {targetThrust} N")
	print(f"Isp: {Isp} m/s")
else:
	print("-----------------------------------------------------------------------------------")
	print("Nozzle-Durchmesser zu groesser als angegebenen Maximalwert, bitte Werte überprüfen!")
	print("-----------------------------------------------------------------------------------")
