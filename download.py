"""
Download Summary of Deposits (SOD) data from FDIC sources.

This script consolidates multiple download methods into a single interface:
- 1987-1993: FDIC FOIA bulk download (ZIP files)
- 1994-2025: FDIC Banks API (JSON to CSV)

Usage:
    # Download all available years
    python download.py --start-year 1987 --end-year 2025

    # Download with API key (recommended for 1994+)
    python download.py --start-year 1994 --end-year 2025 \
        --api-key YOUR_API_KEY

    # Or use environment variable
    export FDIC_API_KEY=YOUR_API_KEY
    python download.py --start-year 1994 --end-year 2025
"""

import requests
import argparse
import sys
import os
import time
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Default output directory (relative to repository root)
DEFAULT_OUTPUT_DIR = 'data/raw'

# FDIC API configuration
FDIC_API_BASE_URL = "https://api.fdic.gov/banks/sod"
FDIC_API_MAX_LIMIT = 10000


def create_session():
    """Create requests session with retry logic."""
    session = requests.Session()

    retry_strategy = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({
        'User-Agent': 'FDIC-SOD-Downloader/2.0',
        'Accept': 'application/json'
    })

    return session


def download_file(url, output_path, delay=1.0):
    """Download a file with progress bar and retry logic.

    Args:
        url: URL to download from
        output_path: Path to save file
        delay: Delay before download (respectful crawling)

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Respectful delay
    if delay > 0:
        time.sleep(delay)

    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        total_size = int(response.headers.get('content-length', 0))

        with open(output_path, 'wb') as f:
            if total_size > 0:
                with tqdm(total=total_size, unit='B', unit_scale=True,
                         desc=output_path.name, leave=False) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if not chunk:
                            continue
                        size = f.write(chunk)
                        pbar.update(size)
            else:
                # No content-length header
                for chunk in response.iter_content(chunk_size=8192):
                    if not chunk:
                        continue
                    f.write(chunk)

        return True

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Failed to download {url}: {e}")
        return False


def get_record_count_api(session, year, api_key=None):
    """Get total record count for a year via API."""
    try:
        params = {
            'filters': f'YEAR:{year}',
            'limit': 0,
            'offset': 0
        }

        if api_key:
            params['api_key'] = api_key

        response = session.get(FDIC_API_BASE_URL, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()
        return data.get('meta', {}).get('total', 0)

    except Exception as e:
        print(f"  [WARNING] Could not get record count: {e}")
        return 0


def download_year_api_chunk(session, year, offset, limit, api_key=None):
    """Download a chunk of data from the API."""
    try:
        params = {
            'filters': f'YEAR:{year}',
            'limit': min(limit, FDIC_API_MAX_LIMIT),
            'offset': offset,
            'sort_by': 'CERT',
            'sort_order': 'ASC'
        }

        if api_key:
            params['api_key'] = api_key

        response = session.get(FDIC_API_BASE_URL, params=params, timeout=60)
        response.raise_for_status()

        data = response.json()
        records = data.get('data', [])

        if not records:
            return None

        # Extract actual data from nested 'data' field
        # API returns: [{'data': {...}, 'score': 0}, ...]
        # We need: [{...}, ...]
        flat_records = [record.get('data', record) for record in records]

        df = pd.DataFrame(flat_records)
        return df

    except Exception as e:
        print(f"  [ERROR] API request failed at offset {offset}: {e}")
        return None


def download_year_api(session, year, output_dir, api_key=None, delay=0.5):
    """Download SOD data for a year using the FDIC API.

    Args:
        session: Requests session
        year: Year to download
        output_dir: Output directory
        api_key: Optional API key
        delay: Delay between API requests

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output_dir) / f"ALL_{year}.csv"

    # Skip if already exists
    if output_path.exists():
        print(f"[{year}] Already exists: ALL_{year}.csv")
        return True

    print(f"[{year}] Downloading via API...")

    # Get total record count
    total_records = get_record_count_api(session, year, api_key)

    if total_records == 0:
        print(f"  [WARNING] No records found for year {year}")
        return False

    print(f"  Total records: {total_records:,}")

    # Download in chunks
    all_chunks = []
    offset = 0

    with tqdm(total=total_records, desc=f"  Progress", unit=" records") as pbar:
        while offset < total_records:
            chunk = download_year_api_chunk(session, year, offset, FDIC_API_MAX_LIMIT, api_key)

            if chunk is None or len(chunk) == 0:
                break

            all_chunks.append(chunk)
            offset += len(chunk)
            pbar.update(len(chunk))

            # Respectful delay between requests
            if offset < total_records:
                time.sleep(delay)

    if not all_chunks:
        print(f"  [ERROR] Failed to download any data for year {year}")
        return False

    # Combine all chunks
    print(f"  Combining {len(all_chunks)} chunks...")
    df = pd.concat(all_chunks, ignore_index=True)

    # Standardize column names to uppercase for consistency with legacy format
    df.columns = df.columns.str.upper()

    # Save to CSV
    print(f"  Saving to: ALL_{year}.csv")
    df.to_csv(output_path, index=False)

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  Successfully saved {len(df):,} records ({file_size_mb:.2f} MB)")

    return True


def download_year_bulk(year, output_dir, delay=1.0):
    """Download SOD data for 1987-1993 via FDIC FOIA bulk download.

    Args:
        year: Year to download (1987-1993)
        output_dir: Output directory
        delay: Delay before download

    Returns:
        True if successful, False otherwise
    """
    url = f'https://www.fdic.gov/foia/sod/sod-{year}.zip'
    filename = f'sod-{year}.zip'
    output_path = Path(output_dir) / filename

    # Skip if already exists
    if output_path.exists():
        print(f"[{year}] Already exists: {filename}")
        return True

    # Download
    print(f"[{year}] Downloading {filename}...")
    success = download_file(url, output_path, delay=delay)

    if success:
        file_size = output_path.stat().st_size / (1024 * 1024)  # MB
        print(f"[{year}] Downloaded {filename} ({file_size:.1f} MB)")
        return True
    else:
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download FDIC Summary of Deposits data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all available years
  python download.py --start-year 1987 --end-year 2025

  # Download with API key (recommended for 1994+)
  python download.py --start-year 1994 --end-year 2025 \
      --api-key YOUR_API_KEY

  # Use environment variable for API key
  export FDIC_API_KEY=YOUR_API_KEY
  python download.py --start-year 1994 --end-year 2025

Data Sources:
  1987-1993: FDIC FOIA bulk download (ZIP files, ~7 MB each)
  1994-2025: FDIC Banks API (CSV files, ~140 MB each)

API Key:
  Not required but recommended to avoid rate limits.
  Register at: https://api.fdic.gov/banks/docs/
  Or use existing key from SOD_API_INFO.md

Notes:
  - Each year contains 70,000-90,000 bank branches
  - Data reflects June 30 of each year
  - API downloads are slower but more reliable
        """
    )

    parser.add_argument(
        '--start-year',
        type=int,
        default=1987,
        help='Start year (default: 1987)'
    )

    parser.add_argument(
        '--end-year',
        type=int,
        default=2025,
        help='End year (default: 2025)'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory (default: {DEFAULT_OUTPUT_DIR})'
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='FDIC API key (or use FDIC_API_KEY environment variable)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=0.5,
        help='Delay between API requests in seconds (default: 0.5)'
    )

    args = parser.parse_args()

    # Get API key from environment if not provided
    api_key = args.api_key or os.environ.get('FDIC_API_KEY')

    # Validate year range
    if args.start_year < 1987:
        print("WARNING: SOD data is only available from 1987 onwards")
        args.start_year = 1987

    if args.start_year > args.end_year:
        print(f"ERROR: Start year ({args.start_year}) cannot be after end year ({args.end_year})")
        sys.exit(1)

    print("="*80)
    print("FDIC SUMMARY OF DEPOSITS DATA DOWNLOAD")
    print("="*80)
    print(f"\nDate range: {args.start_year} - {args.end_year}")
    print(f"Output directory: {args.output_dir}")
    print(f"API key: {'Provided' if api_key else 'Not provided (may have rate limits)'}")
    print(f"Delay between requests: {args.delay}s")
    print("="*80)

    # Create session for API requests
    session = create_session()

    # Download each year
    years = range(args.start_year, args.end_year + 1)
    successful = []
    failed = []

    for year in years:
        try:
            if year <= 1993:
                # Use bulk download
                success = download_year_bulk(year, args.output_dir, delay=args.delay)
            else:
                # Use API
                success = download_year_api(session, year, args.output_dir,
                                           api_key=api_key, delay=args.delay)

            if success:
                successful.append(year)
            else:
                failed.append(year)

        except Exception as e:
            print(f"[{year}] [ERROR] Unexpected error: {e}")
            failed.append(year)

    # Summary
    print("\n" + "="*80)
    print("DOWNLOAD SUMMARY")
    print("="*80)
    print(f"Successfully downloaded: {len(successful)} years")
    if successful:
        print(f"  Years: {min(successful)}-{max(successful)}")

    if failed:
        print(f"\nFailed downloads: {len(failed)} years")
        print(f"  Years: {failed}")

    print("\n" + "="*80)
    print("NEXT STEPS")
    print("="*80)
    print("\n1. Extract and convert to parquet:")
    print(f"   python parse.py \\\n        --input-dir {args.output_dir} \\\n        --output-dir data/processed")

    print("\n2. Verify data:")
    print(f"   python summarize.py \\\n        --input-dir data/processed")

    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
