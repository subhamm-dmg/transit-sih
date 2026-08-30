from pathlib import Path
import pandas as pd


# Find the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Dataset locations
DTC_PATH = PROJECT_ROOT / "data" / "raw" / "dtc_gtfs"
METRO_PATH = PROJECT_ROOT / "data" / "raw" / "gtfs_metro"

def validate_dataset(dataset_path, dataset_name):
    print(f"\n{'=' * 50}")
    print(f"VALIDATING: {dataset_name}")
    print(f"{'=' * 50}")

    # Read the important GTFS files
    trips = pd.read_csv(dataset_path / "trips.txt")
    stop_times = pd.read_csv(dataset_path / "stop_times.txt")
    stops = pd.read_csv(dataset_path / "stops.txt")
    routes = pd.read_csv(dataset_path / "routes.txt")

        # Check duplicate rows
    print("\n--- DUPLICATE CHECK ---")
    print(f"Duplicate routes: {routes.duplicated().sum()}")
    print(f"Duplicate trips: {trips.duplicated().sum()}")
    print(f"Duplicate stops: {stops.duplicated().sum()}")
    print(f"Duplicate stop_times: {stop_times.duplicated().sum()}")


        # Check missing values
    print("\n--- MISSING VALUES CHECK ---")

    for name, df in {
        "routes": routes,
        "trips": trips,
        "stops": stops,
        "stop_times": stop_times
    }.items():

        missing = df.isnull().sum()
        missing = missing[missing > 0]

        if missing.empty:
            print(f"{name}: No missing values")
        else:
            print(f"\n{name}:")
            print(missing)

                # Check duplicate IDs
    print("\n--- DUPLICATE ID CHECK ---")
    print(f"Duplicate route IDs: {routes['route_id'].duplicated().sum()}")
    print(f"Duplicate trip IDs: {trips['trip_id'].duplicated().sum()}")
    print(f"Duplicate stop IDs: {stops['stop_id'].duplicated().sum()}")

        # Check relationships between GTFS files
    print("\n--- RELATIONSHIP CHECK ---")

    # Does every route in trips.txt exist in routes.txt?
    invalid_trip_routes = trips[
        ~trips["route_id"].isin(routes["route_id"])
    ]
    print(
        f"Trips with invalid route_id: "
        f"{len(invalid_trip_routes)}"
    )

    # Does every trip in stop_times.txt exist in trips.txt?
    invalid_stop_time_trips = stop_times[
        ~stop_times["trip_id"].isin(trips["trip_id"])
    ]
    print(
        f"Stop-time records with invalid trip_id: "
        f"{len(invalid_stop_time_trips)}"
    )

    # Does every stop in stop_times.txt exist in stops.txt?
    invalid_stop_time_stops = stop_times[
        ~stop_times["stop_id"].isin(stops["stop_id"])
    ]
    print(
        f"Stop-time records with invalid stop_id: "
        f"{len(invalid_stop_time_stops)}"
    )

validate_dataset(DTC_PATH, "DTC BUS GTFS")
validate_dataset(METRO_PATH, "DELHI METRO GTFS")

    


