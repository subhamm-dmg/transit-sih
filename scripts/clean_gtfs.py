from pathlib import Path
import pandas as pd


# Find the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Raw data locations
DTC_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "dtc_gtfs"
METRO_RAW_PATH = PROJECT_ROOT / "data" / "raw" / "gtfs_metro"

# Cleaned data locations
DTC_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "dtc_gtfs"
METRO_PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "gtfs_metro"

def create_output_folders():
    """Create processed-data folders if they don't already exist."""

    DTC_PROCESSED_PATH.mkdir(parents=True, exist_ok=True)
    METRO_PROCESSED_PATH.mkdir(parents=True, exist_ok=True)

    print("Processed data folders are ready.")

def clean_dtc_trips():
    """Read and clean the DTC trips data."""

    # Read the original trips file
    trips = pd.read_csv(DTC_RAW_PATH / "trips.txt")

    original_rows = len(trips)

    # Remove completely identical duplicate rows
    trips = trips.drop_duplicates()

    cleaned_rows = len(trips)

    print("\nDTC trips cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after removing duplicates: {cleaned_rows}")
    print(f"Duplicates removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = DTC_PROCESSED_PATH / "trips.txt"
    trips.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_dtc_stops():
    """Read and clean the DTC stops data."""

    # Read original stops data
    stops = pd.read_csv(DTC_RAW_PATH / "stops.txt")

    original_rows = len(stops)

    # Remove completely identical duplicate rows
    stops = stops.drop_duplicates()

    # Remove rows missing essential identifiers or coordinates
    stops = stops.dropna(
        subset=["stop_id", "stop_lat", "stop_lon"]
    )

    cleaned_rows = len(stops)

    print("\nDTC stops cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = DTC_PROCESSED_PATH / "stops.txt"
    stops.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_dtc_routes():
    """Read and clean the DTC routes data."""

    # Read original routes data
    routes = pd.read_csv(DTC_RAW_PATH / "routes.txt")

    original_rows = len(routes)

    # Remove completely identical duplicate rows
    routes = routes.drop_duplicates()

    # Remove rows without an essential route ID
    routes = routes.dropna(subset=["route_id"])

    cleaned_rows = len(routes)

    print("\nDTC routes cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = DTC_PROCESSED_PATH / "routes.txt"
    routes.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_dtc_stop_times():
    """Read and validate the DTC stop-times data."""

    # Read original stop-times data
    stop_times = pd.read_csv(
        DTC_RAW_PATH / "stop_times.txt"
    )

    # Read cleaned trip and stop IDs
    cleaned_trips = pd.read_csv(
        DTC_PROCESSED_PATH / "trips.txt"
    )

    cleaned_stops = pd.read_csv(
        DTC_PROCESSED_PATH / "stops.txt"
    )

    original_rows = len(stop_times)

    # Keep only records connected to valid trips
    stop_times = stop_times[
        stop_times["trip_id"].isin(cleaned_trips["trip_id"])
    ]

    # Keep only records connected to valid stops
    stop_times = stop_times[
        stop_times["stop_id"].isin(cleaned_stops["stop_id"])
    ]

    cleaned_rows = len(stop_times)

    print("\nDTC stop_times cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = DTC_PROCESSED_PATH / "stop_times.txt"
    stop_times.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_metro_trips():
    """Read and clean the Delhi Metro trips data."""

    # Read original Metro trips data
    trips = pd.read_csv(METRO_RAW_PATH / "trips.txt")

    original_rows = len(trips)

    # Remove completely identical duplicate rows
    trips = trips.drop_duplicates()

    # Remove rows without essential IDs
    trips = trips.dropna(
        subset=["route_id", "trip_id", "service_id"]
    )

    cleaned_rows = len(trips)

    print("\nMetro trips cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = METRO_PROCESSED_PATH / "trips.txt"
    trips.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_metro_stops():
    """Read and clean the Delhi Metro stops data."""

    # Read original Metro stops data
    stops = pd.read_csv(METRO_RAW_PATH / "stops.txt")

    original_rows = len(stops)

    # Remove completely identical duplicate rows
    stops = stops.drop_duplicates()

    # Remove rows missing essential information
    stops = stops.dropna(
        subset=["stop_id", "stop_name", "stop_lat", "stop_lon"]
    )

    cleaned_rows = len(stops)

    print("\nMetro stops cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = METRO_PROCESSED_PATH / "stops.txt"
    stops.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_metro_routes():
    """Read and clean the Delhi Metro routes data."""

    # Read original Metro routes data
    routes = pd.read_csv(METRO_RAW_PATH / "routes.txt")

    original_rows = len(routes)

    # Remove completely identical duplicate rows
    routes = routes.drop_duplicates()

    # Remove rows missing the essential route ID
    routes = routes.dropna(subset=["route_id"])

    cleaned_rows = len(routes)

    print("\nMetro routes cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = METRO_PROCESSED_PATH / "routes.txt"
    routes.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

def clean_metro_stop_times():
    """Read and clean the Delhi Metro stop-times data."""

    # Read original stop-times data
    stop_times = pd.read_csv(
        METRO_RAW_PATH / "stop_times.txt"
    )

    # Read cleaned trips and stops
    cleaned_trips = pd.read_csv(
        METRO_PROCESSED_PATH / "trips.txt"
    )

    cleaned_stops = pd.read_csv(
        METRO_PROCESSED_PATH / "stops.txt"
    )

    original_rows = len(stop_times)

    # Keep only records connected to valid trips
    stop_times = stop_times[
        stop_times["trip_id"].isin(cleaned_trips["trip_id"])
    ]

    # Keep only records connected to valid stops
    stop_times = stop_times[
        stop_times["stop_id"].isin(cleaned_stops["stop_id"])
    ]

    # Remove completely identical duplicate rows
    stop_times = stop_times.drop_duplicates()

    cleaned_rows = len(stop_times)

    print("\nMetro stop_times cleaning:")
    print(f"Original rows: {original_rows}")
    print(f"Rows after cleaning: {cleaned_rows}")
    print(f"Rows removed: {original_rows - cleaned_rows}")

    # Save cleaned data
    output_file = METRO_PROCESSED_PATH / "stop_times.txt"
    stop_times.to_csv(output_file, index=False)

    print(f"Saved cleaned file to: {output_file}")

create_output_folders()
clean_dtc_trips()
clean_dtc_stops()
clean_dtc_routes()
clean_dtc_stop_times()

clean_metro_trips()
clean_metro_stops()
clean_metro_routes()
clean_metro_stop_times()
