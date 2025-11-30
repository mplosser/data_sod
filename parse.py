"""
Extract Summary of Deposits data from ZIP files to parquet format.

This script processes downloaded SOD files (ZIP or CSV) and converts them to
standardized parquet format with parallelization support.

Handles multiple file formats:
- sod-{year}.zip (1987-1993): FDIC FOIA format
- ALL_{year}.zip (1994-2023): FDIC Dynamic Download format
- ALL_{year}.csv (2024+): BankFind Suite format

Usage:
    # Extract all files with default parallelization
    python parse.py \\
        --input-dir data/raw \\
        --output-dir data/processed

    # Specify number of workers
    python parse.py \\
        --input-dir data/raw \\
        --output-dir data/processed \\
        --workers 8

    # Disable parallelization
    python parse.py \\
        --input-dir data/raw \\
        --output-dir data/processed \\
        --no-parallel
"""

import pandas as pd
import zipfile
import argparse
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import re

def extract_year_from_filename(filename):
    """
    Extract year from filename.

    Handles formats:
    - sod-1987.zip -> 1987
    - ALL_2020.zip -> 2020
    - ALL_2024.csv -> 2024

    Returns:
        Year as integer or None if not found
    """
    # Try sod-{year}.zip format
    match = re.search(r'sod-(\d{4})', filename)
    if match:
        return int(match.group(1))

    # Try ALL_{year} format
    match = re.search(r'ALL_(\d{4})', filename)
    if match:
        return int(match.group(1))

    return None


def process_sod_zip(zip_path):
    """
    Extract SOD data from ZIP file.

    Args:
        zip_path: Path to ZIP file

    Returns:
        DataFrame with standardized columns
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Find CSV file (varies by year)
        csv_files = [f for f in zf.namelist() if f.lower().endswith('.csv')]

        if not csv_files:
            raise ValueError(f"No CSV found in {zip_path}")

        # Read first CSV
        with zf.open(csv_files[0]) as f:
            # Try different encodings
            try:
                df = pd.read_csv(f, encoding='utf-8', low_memory=False)
            except UnicodeDecodeError:
                f.seek(0)
                df = pd.read_csv(f, encoding='latin-1', low_memory=False)

    return df


def process_sod_csv(csv_path):
    """
    Read SOD data from CSV file (2024+ format).

    Args:
        csv_path: Path to CSV file

    Returns:
        DataFrame with standardized columns
    """
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding='latin-1', low_memory=False)

    return df


def standardize_sod_data(df, year):
    """
    Standardize SOD DataFrame.

    - Uppercase column names
    - Add REPORTING_PERIOD
    - Convert CERT to integer
    - Order columns consistently

    Args:
        df: Raw DataFrame
        year: Year of data

    Returns:
        Standardized DataFrame
    """
    # Uppercase column names and strip whitespace
    df.columns = [str(col).upper().strip() for col in df.columns]

    # Add REPORTING_PERIOD (June 30 of year)
    df['REPORTING_PERIOD'] = pd.Timestamp(year=year, month=6, day=30)

    # Ensure CERT is integer (primary identifier)
    if 'CERT' in df.columns:
        df['CERT'] = pd.to_numeric(df['CERT'], errors='coerce')
        df = df.dropna(subset=['CERT'])
        df['CERT'] = df['CERT'].astype(int)
    else:
        raise ValueError(f"CERT column not found in data for year {year}")

    # Standardize column order
    id_cols = ['CERT', 'REPORTING_PERIOD']

    # Add other identifier columns if they exist
    optional_id_cols = ['UNINUMBR', 'BRNUM', 'YEAR']
    for col in optional_id_cols:
        if col in df.columns and col not in id_cols:
            id_cols.append(col)

    # Data columns (alphabetical)
    data_cols = sorted([c for c in df.columns if c not in id_cols])

    # Reorder
    df = df[id_cols + data_cols]

    return df


def process_file_wrapper(args_tuple):
    """
    Wrapper function for parallel processing.

    Args:
        args_tuple: (file_path_str, output_dir_str)

    Returns:
        Tuple of (status, year, message)
    """
    file_path_str, output_dir_str = args_tuple

    file_path = Path(file_path_str)
    output_dir = Path(output_dir_str)

    try:
        # Extract year from filename
        year = extract_year_from_filename(file_path.name)

        if year is None:
            return ('error', None, f"Could not extract year from {file_path.name}")

        # Check if already processed
        output_path = output_dir / f"{year}.parquet"
        if output_path.exists():
            return ('skipped', year, "Already exists")

        # Process based on file type
        if file_path.suffix.lower() == '.zip':
            df = process_sod_zip(file_path)
        elif file_path.suffix.lower() == '.csv':
            df = process_sod_csv(file_path)
        else:
            return ('error', year, f"Unsupported file type: {file_path.suffix}")

        # Standardize
        df = standardize_sod_data(df, year)

        # Save as parquet
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=False, compression='snappy')

        return ('success', year, f"{len(df):,} branches, {len(df.columns)-2} variables")

    except Exception as e:
        import traceback
        error_msg = f"Error processing {file_path.name}: {str(e)}\n{traceback.format_exc()}"
        return ('error', None, error_msg)


def main():
    parser = argparse.ArgumentParser(
        description='Extract SOD data from ZIP/CSV files to parquet format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract with default parallelization (all CPUs)
  python parse.py \\
      --input-dir data/raw \\
      --output-dir data/processed

  # Limit to 4 workers
  python parse.py \\
      --input-dir data/raw \\
      --output-dir data/processed \\
      --workers 4

  # Disable parallelization
  python parse.py \\
      --input-dir data/raw \\
      --output-dir data/processed \\
      --no-parallel

Output Format:
  - Annual parquet files: {YEAR}.parquet
  - Columns: CERT, REPORTING_PERIOD, ... (alphabetical)
  - All numeric values preserved as-is
        """
    )

    parser.add_argument(
        '--input-dir',
        type=str,
        default='data/raw',
        help='Directory containing downloaded ZIP/CSV files (default: data/raw)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/processed',
        help='Directory to save parquet files (default: data/processed)'
    )

    parser.add_argument(
        '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: all CPUs)'
    )

    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing'
    )

    parser.add_argument(
        '--start-year',
        type=int,
        help='Only process files from this year onwards'
    )

    parser.add_argument(
        '--end-year',
        type=int,
        help='Only process files up to this year'
    )

    args = parser.parse_args()

    # Setup paths
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"ERROR: Input directory does not exist: {input_dir}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    # Find files to process
    files_to_process = (
        list(input_dir.glob('*.zip')) +
        list(input_dir.glob('*.ZIP')) +
        list(input_dir.glob('*.csv')) +
        list(input_dir.glob('*.CSV'))
    )

    # Filter by year if specified
    if args.start_year or args.end_year:
        filtered_files = []
        for f in files_to_process:
            year = extract_year_from_filename(f.name)
            if year is None:
                continue
            if args.start_year and year < args.start_year:
                continue
            if args.end_year and year > args.end_year:
                continue
            filtered_files.append(f)
        files_to_process = filtered_files

    files_to_process.sort()

    if not files_to_process:
        print("No files found to process")
        return 1

    # Determine worker count
    if args.no_parallel:
        workers = 1
    elif args.workers:
        workers = args.workers
    else:
        workers = multiprocessing.cpu_count()

    print("="*80)
    print("SOD DATA EXTRACTION")
    print("="*80)
    print(f"Input directory: {input_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Files to process: {len(files_to_process)}")
    print(f"Parallel workers: {workers}")
    print("="*80)

    # Process files
    successful = []
    skipped = []
    failed = []

    if workers == 1:
        # Sequential processing
        print("\nProcessing sequentially...")
        for file_path in files_to_process:
            status, year, message = process_file_wrapper((str(file_path), str(output_dir)))

            if status == 'success':
                successful.append(year)
                print(f"[{year}] {message}")
            elif status == 'skipped':
                skipped.append(year)
                print(f"[{year}] {message}")
            else:
                failed.append(year if year else file_path.name)
                print(f"[ERROR] {message}")

    else:
        # Parallel processing
        print(f"\nProcessing in parallel with {workers} workers...")

        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(process_file_wrapper, (str(f), str(output_dir))): f
                for f in files_to_process
            }

            # Process results as they complete
            completed = 0
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                completed += 1

                try:
                    status, year, message = future.result()

                    if status == 'success':
                        successful.append(year)
                        print(f"[{year}] {message}")
                    elif status == 'skipped':
                        skipped.append(year)
                        print(f"[{year}] {message}")
                    else:
                        failed.append(year if year else file_path.name)
                        print(f"[ERROR] {message}")

                except Exception as e:
                    print(f"[ERROR] Unexpected error processing {file_path.name}: {e}")
                    failed.append(file_path.name)

                # Progress update
                if completed % 5 == 0 or completed == len(files_to_process):
                    print(f"  Progress: {completed}/{len(files_to_process)} files processed")

    # Summary
    print("\n" + "="*80)
    print("EXTRACTION SUMMARY")
    print("="*80)
    print(f"Successfully processed: {len(successful)} files")
    if successful:
        print(f"  Years: {min(successful)}-{max(successful)}")

    if skipped:
        print(f"\nSkipped (already exist): {len(skipped)} files")
        if len(skipped) <= 10:
            print(f"  Years: {sorted(skipped)}")

    if failed:
        print(f"\nFailed: {len(failed)} files")
        print(f"  {failed}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\nVerify the extracted data:")
    print(f"  python summarize.py --input-dir {output_dir}")

    return 0 if not failed else 1


if __name__ == '__main__':
    sys.exit(main())
