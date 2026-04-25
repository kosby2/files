"""Data models for multi-branch logistics"""

from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class Stop:
    branch_id: str
    stop_id: str
    address: str
    latitude: float
    longitude: float
    service_time_minutes: int
    profit_per_stop: float
    time_window_start: str
    time_window_end: str
    priority: str

@dataclass
class Vehicle:
    branch_id: str
    vehicle_id: str
    truck_year: int
    current_mileage: int
    last_maintenance_days_ago: int
    capacity_units: int
    daily_cost: float
    est_failure_rate_pct: float

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
    profit: float
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
class FailureSimulationResult:
    branch_id: str
    simulation_num: int
    failed_vehicles: List[str]
    routes: List[Route]
    stops_serviced: int
    stops_missed: List[str]
    total_profit: float
    success_rate: float

@dataclass
class BranchFailureAnalysis:
    branch_id: str
    total_simulations: int
    expected_profit: float
    profit_std_dev: float
    service_reliability: Dict[str, float]  # stop_id -> success_rate
    vehicle_failure_frequency: Dict[str, int]  # vehicle_id -> times_failed
    critical_stops: List[str]  # stops with <80% success rate
