from pathlib import Path
import pandas as pd


# Find the main project folder
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Locations of our datasets
DTC_PATH = PROJECT_ROOT / "data" / "raw" / "dtc_gtfs"
METRO_PATH = PROJECT_ROOT / "data" / "raw" / "gtfs_metro"


def explore_dataset(dataset_path, dataset_name):
    print(f"\n{'=' * 50}")
    print(f"EXPLORING: {dataset_name}")
    print(f"{'=' * 50}")

    # Find all .txt files
    files = list(dataset_path.glob("*.txt"))

    if not files:
        print("No .txt files found!")
        return

    for file in files:
        print(f"\nFILE: {file.name}")

        try:
            # Read the GTFS file
            df = pd.read_csv(file)

            print(f"Rows: {len(df)}")
            print(f"Columns: {len(df.columns)}")
            print("Column names:")
            print(list(df.columns))

            print("\nFirst 3 rows:")
            print(df.head(3))

        except Exception as error:
            print(f"Could not read this file: {error}")


# Explore both datasets
explore_dataset(DTC_PATH, "DTC BUS GTFS")
explore_dataset(METRO_PATH, "DELHI METRO GTFS")