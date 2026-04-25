"""Data models for multi-branch logistics"""

from dataclasses import dataclass
from typing import List, Dict, Optional



@dataclass
class Vehicle: #update
    branch_id: str
    vehicle_id: str
    truck_year: int
    current_mileage: int
    last_maintenance_days_ago: int
    capacity_units: int
    daily_cost: float
    est_failure_rate_pct: float
    max_route_minutes: int = 480  # 8 hours

@dataclass
class Depot:
    branch_id: str
    depot_id: str
    latitude: float
    longitude: float
    name: str

@dataclass
class RouteStop:
    stop_id: str
    address: str
    revenue: float
    service_time: int
    time_window: str
    arrival_time: Optional[str] = None
    departure_time: Optional[str] = None

@dataclass
class Route:
    vehicle_id: str
    stops: List[RouteStop]
    total_profit: float
    daily_cost: float
    net_profit: float
    stops_count: int
    total_distance: Optional[float] = None
    total_time: Optional[int] = None

@dataclass
class BranchSolution:
    branch_id: str
    routes: List[Route]
    total_routes: int
    total_profit: float
    total_cost: float
    net_profit: float
    stops_serviced: int
    stops_missed: int



@dataclass
class BranchFailureAnalysis:
    branch_id: str
    total_simulations: int
    expected_profit: float
    profit_std_dev: float
    service_reliability: Dict[str, float]  # stop_id -> success_rate
    vehicle_failure_frequency: Dict[str, int]  # vehicle_id -> times_failed
    critical_stops: List[str]  # stops with <80% success rate
