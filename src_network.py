"""Multi-branch logistics network solver with failure simulation"""

import pandas as pd
import numpy as np
import random
import json
from typing import Dict, List
from datetime import datetime
from venv import logger

from src_models import (
    Stop, Vehicle, Depot, 
    FailureSimulationResult, BranchFailureAnalysis
)
from src_branch_solver import BranchVRPSolver

class LogisticsNetwork:
    """Manages and solves multiple branches"""
    
    def __init__(self, excel_file: str):
        self.excel_file = excel_file
        self.branches: Dict[str, BranchVRPSolver] = {}
        self.stops_df = None
        self.vehicles_df = None
        self.depots_df = None
        self.parameters = None
        self.load_data()
    
    def load_data(self):
        """Load all data from Excel and initialize branches"""
        self.stops_df = pd.read_excel(self.excel_file, sheet_name='Stops')
        self.vehicles_df = pd.read_excel(self.excel_file, sheet_name='Vehicles')
        self.depots_df = pd.read_excel(self.excel_file, sheet_name='Depots')
        self.parameters = pd.read_excel(self.excel_file, sheet_name='Parameters')
        
        # Initialize branch solvers
        for branch_id in self.stops_df['Branch_ID'].unique():
            self.initialize_branch(branch_id)

        #Convert time windows to Strings
        self.stops_df['Time_Window_Start'] = pd.to_datetime(
        self.stops_df['Time_Window_Start'], format='%H:%M'
        ).dt.strftime('%H:%M')
        
        self.stops_df['Time_Window_End'] = pd.to_datetime(
            self.stops_df['Time_Window_End'], format='%H:%M'
        ).dt.strftime('%H:%M')

    def initialize_branch(self, branch_id: str):
        """Create a BranchVRPSolver for a specific branch"""
        # Get data for this branch
        branch_stops = self.stops_df[self.stops_df['Branch_ID'] == branch_id]
        branch_vehicles = self.vehicles_df[self.vehicles_df['Branch_ID'] == branch_id]
        branch_depot = self.depots_df[self.depots_df['Branch_ID'] == branch_id].iloc[0]
        
        
        # Convert to model objects
        stops = [
            Stop(
                branch_id=row['Branch_ID'],
                stop_id=row['Stop_ID'],
                address=row['Address'],
                latitude=row['Latitude'],
                longitude=row['Longitude'],
                service_time_minutes=row['Service_Time_Minutes'],
                profit_per_stop=row['Profit_Per_Stop'],
                time_window_start=row['Time_Window_Start'],
                time_window_end=row['Time_Window_End'],
                priority=row['Priority']
            )
            for idx, row in branch_stops.iterrows()
        ]
        
        vehicles = [
            Vehicle(
                branch_id=row['Branch_ID'],
                vehicle_id=row['Vehicle_ID'],
                truck_year=row['Truck_Year'],
                current_mileage=row['Current_Mileage'],
                last_maintenance_days_ago=row['Last_Maintenance_Days_Ago'],
                capacity_units=row['Capacity_Units'],
                daily_cost=row['Daily_Cost'],
                est_failure_rate_pct=row['Est_Failure_Rate_%']
            )
            for idx, row in branch_vehicles.iterrows()
        ]
        
        depot = Depot(
            branch_id=branch_depot['Branch_ID'],
            depot_id=branch_depot['Depot_ID'],
            latitude=branch_depot['Latitude'],
            longitude=branch_depot['Longitude'],
            name=branch_depot['Name']
        )
        
        # Create solver
        self.branches[branch_id] = BranchVRPSolver(branch_id, stops, vehicles, depot)
        print(f"Initialized {branch_id}: {len(stops)} stops, {len(vehicles)} vehicles")
    
    def solve_all_branches(self) -> Dict[str, any]:
        """Solve VRP for all branches independently"""
        results = {}
        
        for branch_id, solver in self.branches.items():
            print(f"\nSolving {branch_id}...")
            
            solution = solver.solve() #Solver1
            results[branch_id] = solution
        
        return results
    
    def print_solution(self, results: Dict):
    
        total_network_profit = 0
        total_network_cost = 0

     
        for branch_id, solution in results.items():
            print("\n" + "="*70)
            print(f"BRANCH: {branch_id}")
            print("="*70)

            # Handle infeasible / missing solution
            if solution is None:
                print("No feasible solution found (solver returned None).")
                continue

            # Defensive check in case of malformed objects
            required_attrs = [
                "total_routes", "stops_serviced", "stops_missed",
                "total_profit", "total_cost", "net_profit", "routes"
            ]
            if not all(hasattr(solution, attr) for attr in required_attrs):
                print(f"Invalid solution object: {solution}")
                continue

            print(f"Routes: {solution.total_routes}")
            print(f"Stops Serviced: {solution.stops_serviced}")
            print(f"Stops Missed: {solution.stops_missed}")
            print(f"Revenue: ${solution.total_profit:.2f}")
            print(f"Cost: ${solution.total_cost:.2f}")
            print(f"Net Profit: ${solution.net_profit:.2f}")

            print("\nRoutes:")
            for route in solution.routes:
                # Guard route structure
                if not hasattr(route, "stops"):
                    print(f"  Invalid route object: {route}")
                    continue

                print(f"\n  {getattr(route, 'vehicle_id', 'UNKNOWN')} "
                    f"({getattr(route, 'stops_count', 'N/A')} stops)")

                for stop in route.stops:
                    if getattr(stop, "stop_id", None) == 'DEPOT':
                        print(f"    → [{stop.stop_id}] {getattr(stop, 'address', '')}")
                    else:
                        print(
                            f"    → {getattr(stop, 'stop_id', 'UNKNOWN')} "
                            f"{getattr(stop, 'address', '')} "
                            f"(${getattr(stop, 'profit', 0)}, "
                            f"{getattr(stop, 'service_time', 0)}min)"
                        )

                print(f"    Net: ${getattr(route, 'net_profit', 0):.2f}")

            total_network_profit += solution.total_profit
            total_network_cost += solution.total_cost

        print("\n" + "="*70)
        print("NETWORK SUMMARY")
        print("="*70)
        print(f"Total Revenue: ${total_network_profit:.2f}")
        print(f"Total Cost: ${total_network_cost:.2f}")
        print(f"Total Net Profit: ${total_network_profit - total_network_cost:.2f}")
        



