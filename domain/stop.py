from dataclasses import dataclass
from typing import List, Dict, Optional

from dataclasses import dataclass
from typing import Optional


@dataclass
class Stop:
    stop_id: str
    branch_id: str
    customer_id: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    service_time_minutes: int = 0
    load_units: int = 0

    revenue_per_stop: float = 0.0
    internal_service_cost: float = 0.0

    missed_day_penalty: float = 0.0
    days_late: int = 0
    can_defer: bool = True
    mandatory_today: bool = False

    requires_two_person_crew: bool = False
    requires_special_vehicle: bool = False
    time_window_start: Optional[int] = None
    time_window_end: Optional[int] = None

    priority: int = 0
    notes: Optional[str] = None

    @property
    def net_value(self) -> float:
        """
        Estimated economic value of serving this stop today,
        before travel cost is considered.
        """
        return self.revenue_if_served - self.internal_service_cost

    @property
    def required_crew_size(self) -> int:
        """
        Converts safety requirements into a simple routing rule.
        """
        return 2 if self.requires_two_person_crew else 1

    @property
    def has_time_window(self) -> bool:
        return (
            self.time_window_start_minutes is not None
            and self.time_window_end_minutes is not None
        )

    def calculate_drop_penalty(self) -> int:
        """
        Penalty used by OR-Tools if this stop is skipped.

        Mandatory stops should usually not use this value, because
        mandatory stops should not be added as optional disjunctions.
        """
        if self.mandatory_today:
            return 0

        penalty = 0.0

        penalty += max(self.net_value, 0.0)
        penalty += self.missed_day_penalty

        if self.days_late > 0:
            penalty += self.days_late * self.missed_day_penalty

        penalty += self.priority

        if self.can_defer and self.missed_day_penalty == 0:
            penalty = min(penalty, max(self.net_value, 1.0))

        return int(max(round(penalty), 0))

    def is_serviceable_by_crew_size(self, crew_size: int) -> bool:
        return crew_size >= self.required_crew_size

    def validate(self) -> None:
        """
        Basic sanity checks before converting the stop into an OR-Tools node.
        """
        if self.service_minutes < 0:
            raise ValueError(f"Stop {self.stop_id} has negative service_minutes.")

        if self.load_units < 0:
            raise ValueError(f"Stop {self.stop_id} has negative load_units.")

        if self.days_late < 0:
            raise ValueError(f"Stop {self.stop_id} has negative days_late.")

        if self.time_window_start_minutes is not None and self.time_window_end_minutes is not None:
            if self.time_window_start_minutes > self.time_window_end_minutes:
                raise ValueError(f"Stop {self.stop_id} has an invalid time window.")