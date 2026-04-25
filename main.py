#!/usr/bin/env python3
"""
Main
"""

import json
from src_network import LogisticsNetwork

def main():
    print("="*70)
    print("MULTI-BRANCH LOGISTICS NETWORK SOLVER")
    print("="*70)
    
    # Load network
    print("\nLoading network data...")
    network = LogisticsNetwork('logistics_data_multibranch.xlsx')
    
    # Solve all branches (optimistic scenario)
    print("\n" + "="*70)
    print("PHASE 1: OPTIMISTIC SOLUTION (All trucks working)")
    print("="*70)
    optimistic_results = network.solve_all_branches()
    network.print_solution(optimistic_results)
    
    # Save optimistic solution
    optimistic_json = {
        branch_id: {
            'routes': [
                {
                    'vehicle_id': str(route.vehicle_id),
                    'stops': [
                        {
                            'stop_id': str(stop.stop_id),
                            'address': str(stop.address),
                            'profit': float(stop.profit),
                            'service_time': int(stop.service_time)
                        }
                        for stop in route.stops
                    ],
                    'total_profit': float(route.total_profit),
                    'daily_cost': float(route.daily_cost),
                    'net_profit': float(route.net_profit)
                }
                for route in solution.routes
            ],
            'summary': {
                'total_routes': int(solution.total_routes),
                'total_profit': float(solution.total_profit),
                'total_cost': float(solution.total_cost),
                'net_profit': float(solution.net_profit),
                'stops_serviced': int(solution.stops_serviced),
                'stops_missed': int(solution.stops_missed)
            }
        }
        for branch_id, solution in optimistic_results.items()
    }
    
    with open('results/optimistic_solution.json', 'w') as f:
        json.dump(optimistic_json, f, indent=2)
    
  
    
   
 
    
 
    

    

if __name__ == '__main__':
    main()
