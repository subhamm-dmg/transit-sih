"""
backend/app/services/gov_service.py — Government & Transport Authority Intelligence Engine.

Provides network stress analysis, bottleneck detection, ridership economics,
corridor load tracking, 24-hour demand forecasting, and policy intervention simulation.
"""

from typing import Optional
from app.models.schemas import (
    CorridorMetrics,
    GovAlert,
    GovDemandPoint,
    GovDemandResponse,
    GovOverviewResponse,
    SimulateActionResponse,
)


class GovernmentService:
    """Provides operational insights and decision simulation for transport authorities."""

    def __init__(self):
        self._corridors_db = [
            CorridorMetrics(
                id="R9",
                name="Ring Road High-Frequency Arterial",
                color="purple",
                time=42,
                demand=14200,
                crowd=86,
                delay=6,
                reliability=88,
                revenue=480000,
                transfers=1,
                type="OPTIMAL NETWORK OPTION",
                score=92,
                path=["dhaula_kuan", "aiims", "lajpat_nagar", "sarai_kale_khan", "kashmere_gate"],
            ),
            CorridorMetrics(
                id="R6",
                name="Kashmere Gate – Connaught Place Central Trunk",
                color="teal",
                time=28,
                demand=18900,
                crowd=91,
                delay=4,
                reliability=94,
                revenue=620000,
                transfers=0,
                type="FASTEST NETWORK OPTION",
                score=95,
                path=["kashmere_gate", "chandni_chowk", "new_delhi", "rajiv_chowk", "central_secretariat"],
            ),
            CorridorMetrics(
                id="R3",
                name="South Delhi Okhla – Hauz Khas Feeder",
                color="amber",
                time=36,
                demand=9800,
                crowd=72,
                delay=5,
                reliability=85,
                revenue=310000,
                transfers=1,
                type="BALANCED MULTI-MODAL",
                score=87,
                path=["iiit_delhi", "govindpuri", "nehru_place", "aiims", "hauz_khas", "iit_delhi"],
            ),
            CorridorMetrics(
                id="R12",
                name="East-West Trans-Yamuna Connector",
                color="blue",
                time=45,
                demand=12400,
                crowd=68,
                delay=7,
                reliability=83,
                revenue=395000,
                transfers=1,
                type="ALTERNATIVE",
                score=84,
                path=["anand_vihar", "laxmi_nagar", "ito", "rajiv_chowk", "karol_bagh"],
            ),
        ]

    def get_overview(self) -> GovOverviewResponse:
        return GovOverviewResponse(
            delay_hotspots=8,
            high_demand_routes=12,
            critical_corridors=5,
            network_load_pct=74,
            avg_delay_min=7,
            peak_demand_per_hour=612,
            active_fleet_count=485,
        )

    def get_corridors(self) -> list[CorridorMetrics]:
        return self._corridors_db

    def get_demand(self, peak_window: str = "08:00 – 10:00 AM") -> GovDemandResponse:
        hourly_data = [
            ("06 AM", 32), ("07 AM", 44), ("08 AM", 68), ("09 AM", 96),
            ("10 AM", 86), ("11 AM", 61), ("12 PM", 48), ("01 PM", 42),
            ("02 PM", 38), ("03 PM", 44), ("04 PM", 59), ("05 PM", 77),
            ("06 PM", 92), ("07 PM", 81), ("08 PM", 60),
        ]
        points = [GovDemandPoint(time=label, demand_index=val) for label, val in hourly_data]
        return GovDemandResponse(
            peak_window=peak_window,
            current_load=74,
            avg_delay=7,
            peak_demand=612,
            hourly_distribution=points,
            forecast_60min="Route 9 demand expected to rise by +13% within the next 45 minutes.",
        )

    def get_alerts(self) -> list[GovAlert]:
        return [
            GovAlert(
                id="ALT-1",
                priority="HIGH",
                title="Hampankatta corridor approaching critical capacity",
                description="Passenger load is predicted to exceed 88% during the morning peak window. Boarding dwell times increasing.",
                corridor="R9",
                suggested_action="Deploy 2 feeder buses and increase headway frequency by 20%.",
            ),
            GovAlert(
                id="ALT-2",
                priority="MEDIUM",
                title="Route 3 delay probability increased to 78%",
                description="Congestion choke point detected near Central Interchange; estimated +11 min delay.",
                corridor="R3",
                suggested_action="Divert non-express demand to Route 6 Coastal Corridor.",
            ),
            GovAlert(
                id="ALT-3",
                priority="LOW",
                title="Outer Sector Link 12 recovering smoothly",
                description="Demand normalized to 41% load with 96% schedule reliability.",
                corridor="R12",
                suggested_action="Maintain standard operational timetable.",
            ),
        ]

    def simulate_action(self, action_type: str, corridor_id: str = "R9") -> SimulateActionResponse:
        """
        Simulates the projected impact of a government operational intervention.
        """
        corridor = next((c for c in self._corridors_db if c.id == corridor_id), self._corridors_db[0])
        before_load = corridor.crowd
        before_delay = corridor.delay

        if action_type == "frequency":
            after_load = max(35, before_load - 19)
            after_delay = max(1, before_delay - 3)
            impact = f"Headway reduced from 10m to 6m. Crowding drops by {before_load - after_load}%."
            roi = 8.8
        elif action_type == "deploy_bus":
            after_load = max(35, before_load - 14)
            after_delay = max(1, before_delay - 4)
            impact = f"2 additional fleet units deployed. Delay reduced from {before_delay}m to {after_delay}m."
            roi = 9.2
        elif action_type == "reroute":
            after_load = max(35, before_load - 11)
            after_delay = max(1, before_delay - 2)
            impact = f"15% passenger demand dynamically guided to parallel line. Network load rebalanced."
            roi = 7.9
        else:
            after_load = before_load
            after_delay = before_delay
            impact = "Action acknowledged. Monitoring corridor metrics."
            roi = 5.0

        return SimulateActionResponse(
            action_type=action_type,
            corridor_id=corridor_id,
            before_load=before_load,
            after_load=after_load,
            before_delay=before_delay,
            after_delay=after_delay,
            estimated_impact=impact,
            roi_score=roi,
        )
