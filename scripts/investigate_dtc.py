from pathlib import Path
import pandas as pd


# Find the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Path to DTC GTFS data
DTC_PATH = PROJECT_ROOT / "data" / "raw" / "dtc_gtfs"


# Read trips data
trips = pd.read_csv(DTC_PATH / "trips.txt")


# Find every row with a duplicated trip_id
duplicate_trips = trips[
    trips["trip_id"].duplicated(keep=False)
].sort_values("trip_id")


print("\n--- DTC DUPLICATE TRIPS ---\n")

print(f"Number of rows involved: {len(duplicate_trips)}")
print(f"Number of unique duplicated trip IDs: "
      f"{duplicate_trips['trip_id'].nunique()}")

print("\nDuplicate trip records:")
print(duplicate_trips.to_string(index=False))

