"""Single-branch VRP solver using OR-Tools"""

from venv import logger
import pandas as pd
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
import json
import ortools


try:
    from ortools.constraint_solver import routing_enums_pb2
    from ortools.constraint_solver import pywrapcp
    ORTOOLS_AVAILABLE = True
except ImportError:
    print("OR-Tools not fully installed")
    ORTOOLS_AVAILABLE = False

from src_models import Stop, Vehicle, Depot, Route, RouteStop, BranchSolution

class BranchVRPSolver:
    """Solves VRP for a single branch"""
    
    def __init__(self, branch_id: str, stops: list, vehicles: list, depot: Depot):
        self.branch_id = branch_id
        self.stops_df = pd.DataFrame([s.__dict__ for s in stops])
        self.vehicles_df = pd.DataFrame([v.__dict__ for v in vehicles])
        self.depot = depot
        self.distance_matrix = None
        self.time_matrix = None
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in miles between two coordinates"""
        R = 3959  # Earth's radius in miles
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def build_distance_matrix(self):
        """Build distance matrix in miles"""
        depot_lat = self.depot.latitude
        depot_lon = self.depot.longitude
        
        # Add depot as first location
        locations = [(depot_lat, depot_lon)]
        locations.extend(zip(self.stops_df['latitude'], self.stops_df['longitude']))
        
        n = len(locations)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i+1, n):
                dist = self.haversine_distance(
                    locations[i][0], locations[i][1],
                    locations[j][0], locations[j][1]
                )
                matrix[i][j] = dist
                matrix[j][i] = dist
        
        self.distance_matrix = matrix
    
    def build_time_matrix(self, avg_speed_mph: int = 30):
        """Build time matrix in minutes"""
        self.time_matrix = (self.distance_matrix / avg_speed_mph * 60).astype(int)
    
    
    
    def create_routing_model(self, num_vehicles: int):
        """Create OR-Tools routing model for this branch"""
        if not ORTOOLS_AVAILABLE:
            return None, None
        
        num_stops = len(self.stops_df)
        
        manager = pywrapcp.RoutingIndexManager(
            num_stops + 1,
            num_vehicles,
            0  # depot index
        )
        
        routing = pywrapcp.RoutingModel(manager)
        
        # Transit callback for distance
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(self.distance_matrix[from_node][to_node] * 1000)
        
        # Transit callback for time
        def time_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(self.time_matrix[from_node][to_node])
        
        # Register callbacks
        distance_callback_index = routing.RegisterTransitCallback(distance_callback)
        time_callback_index = routing.RegisterTransitCallback(time_callback)
        
        # Set distance as cost evaluator
        routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)
        
        # Add time dimension for time windows
        routing.AddDimension(
            time_callback_index,
            slack_max=int(24 * 60),      # slack / waiting time (1440 minutes = 24 hours)
            capacity=int(24 * 60),        # max time per vehicle
            fix_start_cumul_to_zero=False,
            name="Time"
        )
        
        time_dimension = routing.GetDimensionOrDie("Time")
        
        # Set time windows for each stop
        for idx, row in self.stops_df.iterrows():
            node_index = manager.NodeToIndex(idx + 1)
            
            # Parse time window start
            start_time = int(
                datetime.strptime(row['time_window_start'], '%H:%M').hour * 60 +
                datetime.strptime(row['time_window_start'], '%H:%M').minute
            )
            
            # Parse time window end
            end_time = int(
                datetime.strptime(row['time_window_end'], '%H:%M').hour * 60 +
                datetime.strptime(row['time_window_end'], '%H:%M').minute
            )
            
            # Set cumulative time range for this stop
            time_dimension.CumulVar(node_index).SetRange(start_time, end_time)
        
       
        
        return routing, manager


    def solve(self, available_vehicles: list = None) -> BranchSolution:
  
        # Build distance and time matrices
        self.build_distance_matrix()
        self.build_time_matrix()
        
        # Filter vehicles if some are unavailable
        if available_vehicles:
            vehicles_to_use = self.vehicles_df[
                self.vehicles_df['vehicle_id'].isin(available_vehicles)
            ]
        else:
            vehicles_to_use = self.vehicles_df
        
        # Handle case with no vehicles available
        if len(vehicles_to_use) == 0:
            logger.warning(f"No vehicles available for branch {self.branch_id}")
            return BranchSolution(
                branch_id=self.branch_id,
                routes=[],
                total_routes=0,
                total_profit=0,
                total_cost=0,
                net_profit=0,
                stops_serviced=0,
                stops_missed=len(self.stops_df)
            )
        
        # Create routing model
        routing, manager = self.create_routing_model(len(vehicles_to_use))
        
        if routing is None:
            logger.error("Failed to create routing model - OR-Tools not available")
            
            return BranchSolution(
                branch_id=self.branch_id,
                routes=[],
                total_routes=0,
                total_profit=0,
                total_cost=0,
                net_profit=0,
                stops_serviced=0,
                stops_missed=len(self.stops_df)
            )
        
        # Solve - NO PARAMETERS, basic solve
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_parameters.time_limit.seconds = 10
        solution = routing.SolveWithParameters(search_parameters)
       
        
        
        
        # Parse and return solution
        if solution:
            logger.info(f"Found solution with {routing.vehicles()} vehicles")
            return self.parse_solution(solution, routing, manager, vehicles_to_use)
        else:
            logger.warning("No solution found")
            #return self.solve_greedy(available_vehicles)
        
    def parse_solution(self, solution, routing, manager, vehicles_df) -> BranchSolution:
        """
        Parse OR-Tools solution into BranchSolution.
        
        Args:
            solution: OR-Tools routing solution
            routing: OR-Tools routing model
            manager: OR-Tools routing index manager
            vehicles_df: DataFrame of vehicles used in solution
        
        Returns:
            BranchSolution with routes and metrics
        """
        routes = []
        total_profit = 0
        total_cost = 0
        serviced_stops = set()
        
        # Iterate through each vehicle's route
        for vehicle_id in range(routing.vehicles()):
            route_stops = []
            route_profit = 0
            vehicle = vehicles_df.iloc[vehicle_id]
            route_cost = vehicle['daily_cost']
            
            # Start at depot
            index = routing.Start(vehicle_id)
            
            # Traverse route
            while not routing.IsEnd(index):
                node_index = manager.IndexToNode(index)
                
                if node_index == 0:
                    # This is the depot - don't add as a stop, just traverse
                    pass
                else:
                    # Regular stop
                    try:
                        stop = self.stops_df.iloc[node_index - 1]
                        route_stops.append(RouteStop(
                            stop_id=stop['stop_id'],
                            address=stop['address'],
                            profit=stop['profit_per_stop'],
                            service_time=stop['service_time_minutes'],
                            time_window=f"{stop['time_window_start']} - {stop['time_window_end']}"
                        ))
                        route_profit += stop['profit_per_stop']
                        serviced_stops.add(stop['stop_id'])
                    except (IndexError, KeyError) as e:
                        logger.error(f"Error parsing stop at node {node_index}: {e}")
                        continue
                
                # Move to next stop in ortools map 
                index = solution.Value(routing.NextVar(index))
            
            # Only add route if it has actual stops (not just depot)
            if len(route_stops) > 0:
                routes.append(Route(
                    vehicle_id=vehicle['vehicle_id'],
                    stops=route_stops,
                    total_profit=route_profit,
                    daily_cost=route_cost,
                    net_profit=route_profit - route_cost,
                    stops_count=len(route_stops)
                ))
                total_profit += route_profit
                total_cost += route_cost
        
        # Calculate missed stops
        missed_stops = len(self.stops_df) - len(serviced_stops)
        
    
        return BranchSolution(
            branch_id=self.branch_id,
            routes=routes,
            total_routes=len(routes),
            total_profit=total_profit,
            total_cost=total_cost,
            net_profit=total_profit - total_cost,
            stops_serviced=len(serviced_stops),
            stops_missed=missed_stops
        )