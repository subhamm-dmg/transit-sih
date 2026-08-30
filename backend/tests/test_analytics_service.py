from app.services.analytics_service import AnalyticsService


def test_summary_has_real_dtc_counts() -> None:
    service = AnalyticsService()
    result = service.summary()

    assert result["dtc"]["available"] is True
    assert result["dtc"]["stop_count"] > 0
    assert result["dtc"]["route_count"] > 0
    assert result["dtc"]["trip_count"] > 0
    assert result["dtc"]["stop_time_count"] > 0


def test_hourly_demand_buckets_sum_to_total() -> None:
    service = AnalyticsService()
    result = service.demand()

    dtc = next(
        item for item in result["datasets"]
        if item["dataset"] == "DTC"
    )

    hourly_total = sum(
        item["scheduled_departures"]
        for item in dtc["hourly"]
    )

    assert hourly_total > 0


def test_bottlenecks_are_deterministic() -> None:
    service = AnalyticsService()

    first = service.bottlenecks()
    second = service.bottlenecks()

    assert first == second

    dtc = next(
        item for item in first["datasets"]
        if item["dataset"] == "DTC"
    )

    assert dtc["bottlenecks"]


def test_delays_are_honest_about_missing_realtime_data() -> None:
    service = AnalyticsService()
    result = service.delays()

    assert result["delay_data_available"] is False
    assert result["delay_source"] == "no_realtime_vehicle_feed_connected"
