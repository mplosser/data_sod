# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FDIC Summary of Deposits (SOD) Data Pipeline - automates downloading, processing, and analyzing bank branch financial data from 1987-2025 (39 years, ~3 million+ branch records).

## Commands

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
```

### Full Pipeline
```bash
# Download (1987-2025, ~20 min)
python 01_download.py --start-year 1987 --end-year 2025

# Parse to parquet (~2-4 min)
python 02_parse.py --input-dir data/raw --output-dir data/processed

# Verify/summarize
python 03_summarize.py --input-dir data/processed
```

### Common Options
```bash
# With API key (for 1994+ data)
set FDIC_API_KEY=your_key_here   # Windows
export FDIC_API_KEY=your_key    # macOS/Linux

# Limit parallelization
python 02_parse.py --workers 4

# Process specific year range
python 01_download.py --start-year 2020 --end-year 2025
```

## Architecture

### Pipeline
```
01_download.py → 02_parse.py → 03_summarize.py → 04_cleanup.py
(raw ZIP/CSV)    (parquet)     (verification)    (optional)
```

### Dual Source Strategy
- **1987-1993**: FDIC FOIA bulk download (ZIP files) via `download_year_bulk()`
- **1994-2025**: FDIC Banks API v2 (JSON→CSV) via `download_year_api()`

Both sources are unified through `02_parse.py` into standardized parquet files.

### Data Standardization (02_parse.py)
- Uppercase all column names
- Add `REPORTING_PERIOD` (June 30 of year)
- Ensure `CERT` is integer type
- Column order: `CERT`, `REPORTING_PERIOD`, then alphabetical
- Embed variable descriptions from FDIC schema (via PyArrow metadata)

### Variable Descriptions
Parquet files include column-level metadata with descriptions from the FDIC YAML schema. A data dictionary CSV is automatically saved to `data/sod_dictionary.csv` during parsing.

## Key Design Patterns

- **HTTP resilience**: Sessions with retry logic (5 retries, exponential backoff)
- **Parallelization**: `ProcessPoolExecutor` in 02_parse.py and 03_summarize.py
- **Dual encoding**: UTF-8 fallback to Latin-1 for CSV files
- **Chunked API**: 10k records per request with pagination
