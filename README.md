# FDIC Summary of Deposits Data Pipeline

Automated pipeline for downloading and processing FDIC Summary of Deposits (SOD) data (1987-2025).

## Overview

Downloads raw data and converts it to parquet format.

**Data Coverage:**
- **Years**: 1987-2025 (39 years)
- **Frequency**: Annual (as of June 30 each year)
- **Entities**: 70,000-90,000 bank branches per year
- **Variables**: 78-80 variables per year

## Requirements

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Download Data

```bash
# Download all available years (1987-2025)
python 01_download.py --start-year 1987 --end-year 2025

# With API key (recommended to avoid rate limits)
python 01_download.py --start-year 1987 --end-year 2025 --api-key YOUR_API_KEY

# Or use environment variable
export FDIC_API_KEY=YOUR_API_KEY  # macOS/Linux
set FDIC_API_KEY=YOUR_API_KEY     # Windows
python 01_download.py --start-year 1987 --end-year 2025
```

### 2. Parse to Parquet

```bash
# Extract and parse with parallelization (recommended)
python 02_parse.py --input-dir data/raw --output-dir data/processed

# Limit workers for low-memory systems
python 02_parse.py --input-dir data/raw --output-dir data/processed --workers 4

# Force reprocessing of existing files
python 02_parse.py --input-dir data/raw --output-dir data/processed --force

# Save data dictionary to CSV
python 02_parse.py --input-dir data/raw --output-dir data/processed --save-dictionary data/sod_dictionary.csv
```

### 3. Verify Data

```bash
# Generate summary
python 03_summarize.py --input-dir data/processed

# Save summary to CSV
python 03_summarize.py --input-dir data/processed --output-csv sod_summary.csv
```

### 4. View Variable Descriptions

```bash
# View all variable descriptions from a parquet file
python 04_describe.py data/processed/2025.parquet

# View specific variable
python 04_describe.py data/processed/2025.parquet DEPSUMBR

# Search for variables by keyword
python 04_describe.py data/processed/2025.parquet --search deposit
```

### 5. Cleanup (Optional)

After parsing, raw files (ZIP/CSV) are no longer needed. Use `05_cleanup.py` to free disk space:

```bash
# Preview what would be deleted
python 05_cleanup.py --raw --dry-run

# Delete raw files (~5 GB)
python 05_cleanup.py --raw

# Delete everything (raw + processed)
python 05_cleanup.py --all
```

## Data Sources

SOD data comes from two different FDIC sources depending on the year:

| Year Range | Source | Format | Method |
|------------|--------|--------|--------|
| 1987-1993 | [FDIC FOIA](https://www.fdic.gov/foia/sod/index.html) | ZIP (sod-{year}.zip) | Bulk Download |
| 1994-2025 | [FDIC Banks API](https://api.fdic.gov/banks/docs/) | CSV (ALL_{year}.csv) | REST API |

## FDIC API

The FDIC Banks API is used for downloading 1994-2025 data. An API key is optional but recommended to avoid rate limits.

**Get an API Key:**
1. Visit https://api.fdic.gov/banks/docs/
2. Click "Get API Key" and register with your email
3. Use the key via environment variable or `--api-key` argument

**API Details:**
- **Endpoint**: `https://api.fdic.gov/banks/sod`
- **Max records per request**: 10,000
- **Pagination**: Handled automatically by 01_download.py
- **Rate limits**: Use 0.5-1s delay between requests (default: 0.5s)

## Output Format

All data is saved as parquet files in `data/processed/`:

```
data/processed/
├── 1987.parquet
├── 1988.parquet
├── ...
└── 2025.parquet
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
  - Additional variables (alphabetical order)

**Variable Descriptions:**

Parquet files include embedded variable descriptions (similar to Stata variable labels), fetched from the [FDIC schema](https://api.fdic.gov/banks/docs/sod_properties.yaml).

```bash
# Save data dictionary to CSV during parsing
python 02_parse.py --input-dir data/raw --output-dir data/processed --save-dictionary data/sod_dictionary.csv
```

Access descriptions in Python:
```python
import pyarrow.parquet as pq

table = pq.read_table("data/processed/2025.parquet")
for field in table.schema:
    desc = field.metadata.get(b'description', b'').decode() if field.metadata else ''
    print(f"{field.name}: {desc}")
```

## Pipeline Scripts

| Script | Purpose | Input | Output | Time |
|--------|---------|-------|--------|------|
| `01_download.py` | Download SOD data | FDIC sources | ZIP/CSV files | ~15-20 min |
| `02_parse.py` | Convert to parquet | ZIP/CSV files | Parquet files | ~2-4 min |
| `03_summarize.py` | Verify data | Parquet files | Summary table | ~5-10 sec |
| `04_describe.py` | View variable descriptions | Parquet file | Descriptions | instant |
| `05_cleanup.py` | Delete data files | - | - | instant |

**Parallelization** (02_parse.py and 03_summarize.py):
- Default: Uses all CPU cores
- `--workers N`: Limit to N workers
- `--no-parallel`: Sequential processing

**Cleanup options:**
```bash
python 05_cleanup.py --raw          # Delete raw files (ZIP/CSV)
python 05_cleanup.py --processed    # Delete parquet files
python 05_cleanup.py --all          # Delete everything
python 05_cleanup.py --all --dry-run  # Preview what would be deleted
```

## Additional Resources

- **FDIC SOD Overview**: https://www.fdic.gov/resources/bankers/call-reports/summary-of-deposits
- **FDIC Banks API**: https://api.fdic.gov/banks/docs/
- **BankFind Suite**: https://banks.data.fdic.gov/bankfind-suite/
