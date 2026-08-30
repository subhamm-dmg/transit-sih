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
            CorridorMetrics(
                id="R15",
                name="Outer Ring Road Expressway & Airport Link",
                color="teal",
                time=39,
                demand=16300,
                crowd=82,
                delay=5,
                reliability=90,
                revenue=540000,
                transfers=1,
                type="EXPRESS ARTERIAL",
                score=91,
                path=["janakpuri_west", "iit_delhi", "nehru_place", "kalkaji_mandir", "botanical_garden"],
            ),
            CorridorMetrics(
                id="R21",
                name="Mehrauli-Badarpur (MB) Road Tech Corridor",
                color="purple",
                time=48,
                demand=11700,
                crowd=79,
                delay=8,
                reliability=81,
                revenue=370000,
                transfers=1,
                type="SUBURBAN FEEDER",
                score=83,
                path=["saket", "batra_hospital", "tughlakabad", "badarpur_border"],
            ),
            CorridorMetrics(
                id="R28",
                name="Mathura Road – Ashram Flyover Concourse",
                color="amber",
                time=34,
                demand=15800,
                crowd=89,
                delay=7,
                reliability=84,
                revenue=510000,
                transfers=1,
                type="HEAVY COMMUTER TRUNK",
                score=88,
                path=["nizamuddin", "ashram", "friends_colony", "apollo_hospital", "sarita_vihar"],
            ),
            CorridorMetrics(
                id="R34",
                name="GT Karnal Road Inter-State Arterial",
                color="blue",
                time=52,
                demand=13100,
                crowd=74,
                delay=6,
                reliability=86,
                revenue=420000,
                transfers=0,
                type="REGIONAL CONNECTOR",
                score=85,
                path=["kashmere_gate", "azadpur", "jahangirpuri", "narela_terminal"],
            ),
            CorridorMetrics(
                id="R40",
                name="Dwarka Sub-City – Janakpuri West Feeder",
                color="teal",
                time=31,
                demand=10500,
                crowd=65,
                delay=3,
                reliability=92,
                revenue=330000,
                transfers=1,
                type="RESIDENTIAL FEEDER",
                score=89,
                path=["dwarka_sec_21", "dwarka_mor", "uttam_nagar", "janakpuri_west"],
            ),
            CorridorMetrics(
                id="R52",
                name="Vikas Marg Trans-Yamuna Commercial Trunk",
                color="coral",
                time=33,
                demand=17400,
                crowd=93,
                delay=9,
                reliability=79,
                revenue=580000,
                transfers=0,
                type="HIGH CONGESTION ARTERIAL",
                score=82,
                path=["anand_vihar", "preet_vihar", "laxmi_nagar", "ito", "delhi_gate"],
            ),
        ]

    def get_overview(self) -> GovOverviewResponse:
        return GovOverviewResponse(
            delay_hotspots=8,
            high_demand_routes=12,
            critical_corridors=10,
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
                title="Ring Road / Kashmere Gate corridor approaching critical capacity",
                description="Passenger load is predicted to exceed 88% during the morning peak window. Boarding dwell times increasing.",
                corridor="R9",
                suggested_action="Deploy 20 feeder buses and increase headway frequency by 20%.",
            ),
            GovAlert(
                id="ALT-2",
                priority="MEDIUM",
                title="Vikas Marg Trans-Yamuna delay probability increased to 78%",
                description="Congestion choke point detected near ITO Bridge; estimated +11 min delay.",
                corridor="R52",
                suggested_action="Activate dynamic signal priority at ITO and Laxmi Nagar intersections.",
            ),
            GovAlert(
                id="ALT-3",
                priority="LOW",
                title="Outer Ring Road Expressway Line 15 operating optimally",
                description="Demand normalized to 48% load with 95% schedule reliability.",
                corridor="R15",
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

        if action_type in ("deploy_bus", "buses"):
            after_load = max(30, before_load - 18)
            after_delay = max(1, before_delay - 4)
            impact = f"+25 Electric Buses deployed on {corridor.name}. Peak dwell time reduced by 18% and avg delay cut to {after_delay}m."
            roi = 9.4
        elif action_type in ("signal_priority", "signals"):
            after_load = max(30, before_load - 11)
            after_delay = max(1, before_delay - 3)
            impact = f"Transit Signal Priority (TSP) activated at key junctions. Average delay reduced from {before_delay}m to {after_delay}m with 19% on-time gains."
            roi = 9.1
        elif action_type in ("feeder_shuttles", "feeders"):
            after_load = max(30, before_load - 24)
            after_delay = max(1, before_delay - 3)
            impact = f"Dynamic first/last-mile shuttles deployed at Okhla / Tech Hubs. Commuter wait times drop by 24%."
            roi = 8.7
        elif action_type in ("brt_lane", "brt"):
            after_load = max(30, before_load - 20)
            after_delay = max(1, before_delay - 5)
            impact = f"Dedicated Bus Rapid Transit (BRT) lane enforced. Average bus speed improves from 17 km/h to 27 km/h."
            roi = 9.6
        elif action_type in ("offpeak_discount", "pricing"):
            after_load = max(30, before_load - 15)
            after_delay = max(1, before_delay - 2)
            impact = f"20% off-peak fare incentive applied (11 AM - 4 PM). Successfully shifted 14,000 peak commuters to off-peak slots."
            roi = 8.5
        elif action_type in ("metro_frequency", "metro"):
            after_load = max(30, before_load - 22)
            after_delay = max(1, before_delay - 3)
            impact = f"Peak headway boosted to 2.5 min intervals on DMRC trunk lines. Station platform crowding relieved by 22%."
            roi = 9.8
        else:
            after_load = before_load
            after_delay = before_delay
            impact = f"Operational action '{action_type}' applied to {corridor.name}."
            roi = 7.5

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
