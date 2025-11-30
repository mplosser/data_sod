# FDIC Summary of Deposits Data Pipeline

Automated pipeline for downloading and processing FDIC Summary of Deposits (SOD) data (1987-2025).

## Overview

Downloads raw data and converts it to parquet format.

**Data Coverage:**
- **Years**: 1987-2025
- **Frequency**: Annual (as of June 30 each year)
- **Entities**: 70,000-90,000 bank branches per year
- **Variables**: 78-80 variables per year

## Requirements

Install required Python packages before running the scripts:

```bash
pip install -r requirements.txt
```
## Quick Start

### 1. Download Data

```bash
# Download all available years (1987-2025)
python download.py --start-year 1987 --end-year 2025 \
    --api-key YOUR_API_KEY

# Or use environment variable for API key
export FDIC_API_KEY=YOUR_API_KEY
python download.py --start-year 1987 --end-year 2025

# Download specific range
python download.py --start-year 2020 --end-year 2025 \
    --api-key YOUR_API_KEY
```

**API Key** (optional but recommended):
- Not required but helps avoid rate limits
- Get your key from [SOD_API_INFO.md](../SOD_API_INFO.md)
- Or register at: https://api.fdic.gov/banks/docs/

### 2. Extract to Parquet

```bash
# Extract and parse with parallelization (recommended)
python parse.py \
    --input-dir data/raw \
    --output-dir data/processed

# Limit workers for low-memory systems
python parse.py \
    --input-dir data/raw \
    --output-dir data/processed \
    --workers 4
```

### 3. Verify Data

```bash
# Generate summary
python summarize.py --input-dir data/processed

# Save summary to CSV
python summarize.py \
    --input-dir data/processed \
    --output-csv sod_raw_summary.csv
```

## Data Sources

SOD data comes from two different FDIC sources depending on the year:

| Year Range | Source | Format | Method | Automation |
|------------|--------|--------|--------|------------|
| 1987-1993 | [FDIC FOIA](https://www.fdic.gov/foia/sod/index.html) | ZIP (sod-{year}.zip) | Bulk Download | ✅ Automated |
| 1994-2025 | [FDIC Banks API](https://api.fdic.gov/banks/docs/) | JSON→CSV (ALL_{year}.csv) | API | ✅ Automated |

**Why the API?**
- Works for all years 1994-2025
- No manual downloads needed
- Automatic pagination handling
- See [SOD_API_INFO.md](../SOD_API_INFO.md) for details

## Output Format

All data is saved as parquet files in `data/processed/`:

```
data/sod/processed/
├── 1987.parquet
├── 1988.parquet
├── ...
├── 2025.parquet
```

**File Structure:**
- **Rows**: One per bank branch
- **Columns**:
  - `CERT` - FDIC Certificate Number (integer)
  - `REPORTING_PERIOD` - Date (datetime, June 30 of year)
  - `UNINUMBR` - Unique branch number
  - `BRNUM` - Branch number
  - `DEPSUMBR` - Total deposits at branch (in thousands)
  - `STNAME` - State name
  - `CITY` - City
  - Additional variables (alphabetical)

**Coverage:**
- 39 total years (1987-2025)
- ~70,000-90,000 branches per year
- ~78-80 variables per year
- Complete data with no filtering or transformations

## Pipeline Scripts

### Core Scripts

| Script | Purpose | Input | Output | Performance |
|--------|---------|-------|--------|-------------|
| `download.py` | Download SOD data (Bulk/API) | FDIC sources | ZIP/CSV files | ~15-20 min (1994-2025 via API) |
| `parse.py` | Extract ZIP/CSV to parquet (parallel) | ZIP/CSV files | Parquet files | ~2-4 min (39 files) |
| `summarize.py` | Summarize parsed data | Parquet files | Summary table | ~5-10 sec (39 files) |

**Parallelization Options** (available for `parse.py`, `summarize.py`):
- **Default**: Uses all CPU cores for parallel processing
- `--workers N`: Specify number of parallel workers (e.g., `--workers 4`)
- `--no-parallel`: Disable parallel processing (slower but uses less memory)
- **Expected speedup**: 4-8x on multi-core CPUs

**Download Options**:
```bash
# Download with API key (recommended)
python download.py --start-year 1987 --end-year 2025 \
    --api-key YOUR_API_KEY

# Download without API key (may have rate limits)
python download.py --start-year 1987 --end-year 2025

# Adjust delay between API requests
python download.py --start-year 1994 --end-year 2025 \
    --api-key YOUR_API_KEY \
    --delay 1.0
```

**Extraction Options**:
```bash
# Default parallel processing (all CPU cores)
python parse.py \
    --input-dir data/raw \
    --output-dir data/processed

# Limit to 4 workers
python parse.py \
    --input-dir data/raw \
    --output-dir data/processed \
    --workers 4

# Disable parallelization
python parse.py \
    --input-dir data/raw \
    --output-dir data/processed \
    --no-parallel
```


## Additional Resources

- **FDIC SOD Overview**: https://www.fdic.gov/resources/bankers/call-reports/summary-of-deposits
- **FDIC Banks API**: https://api.fdic.gov/banks/docs/
- **BankFind Suite**: https://banks.data.fdic.gov/bankfind-suite/
- **SOD API Guide**: See [SOD_API_INFO.md](../SOD_API_INFO.md) for detailed API documentation
