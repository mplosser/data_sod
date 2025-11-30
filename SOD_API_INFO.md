# FDIC Banks API for Summary of Deposits Data

## Overview

The FDIC provides a public API for accessing Summary of Deposits (SOD) data that is **more reliable and comprehensive** than downloading ZIP files. The API works for all years from 1987 to present (including 2025).

**API Documentation**: https://api.fdic.gov/banks/docs/

## Getting Started

### Your API Key

You have a registered API key:
- **Email**: mplosser@gmail.com
- **API Key**: `NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K`

Set it as an environment variable (recommended):
```bash
# Windows (Command Prompt)
set FDIC_API_KEY=NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K

# Windows (PowerShell)
$env:FDIC_API_KEY="NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K"

# macOS/Linux
export FDIC_API_KEY=NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K
```

Or provide it directly to scripts:
```bash
python download_sod_data_api.py --api-key NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K
```

## Data Availability

**COMPLETE COVERAGE AVAILABLE**: All years **1987-2025** can be downloaded!

- **1987-1993** (7 years): Available via [FDIC Bulk Historical Download](https://www.fdic.gov/foia/summary-deposits-data-bulk-download)
  - Use `download_sod_bulk_historical.py` script
- **1994-2025** (32 years): Available via FDIC Banks API (this page)
  - Use `download_sod_data_api.py` script

## Why Use the API?

### Advantages over ZIP File Downloads

| Feature | API Method (1994-2025) | Bulk Historical (1987-1993) |
|---------|------------------------|----------------------------|
| **Years Available** | 1994-2025 (32 years) | 1987-1993 (7 years) |
| **Reliability** | ✅ Always available | ✅ Always available |
| **Format** | ✅ CSV (no extraction) | ⚠️ ZIP files need extraction |
| **Automation** | ✅ Fully automated | ✅ Fully automated |
| **Pagination** | ✅ Automatic | N/A |
| **Download Speed** | ⚠️ Slower (~10 min) | ✅ Very fast (~13 sec) |
| **File Size** | ⚠️ Large (4.5 GB) | ✅ Small (40 MB zipped) |
| **Latest Data (2025)** | ✅ Available now | N/A |
| **Complete Coverage** | **Together: 1987-2025 (ALL 39 years)** | |

## API Endpoint

**Base URL**: `https://api.fdic.gov/banks/sod`

**Note**: The correct endpoint is `/banks/sod` (NOT `/banks/v1/sod`)

**Method**: GET

**Authentication**: None required (public API)

## Key Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `filters` | Filter records | `YEAR:2025` |
| `fields` | Specific fields to return | `CERT,RSSDID,DEPSUMBR` |
| `limit` | Records per request (max 10,000) | `10000` |
| `offset` | Pagination offset | `0` |
| `sort_by` | Sort field | `CERT` |
| `sort_order` | ASC or DESC | `ASC` |
| `format` | Response format | `json` or `csv` |

## Available Fields

The API returns 120+ fields including:

### Key Identifiers
- `CERT` - FDIC Certificate Number
- `RSSDID` - Federal Reserve RSSD ID
- `UNINUMBR` - Unique branch number

### Institution Info
- `NAMEFULL` - Institution name (main office)
- `NAMEBR` - Branch name
- `YEAR` - Data year

### Financial Data
- `DEPSUMBR` - Branch deposits (domestic)
- `ASSET` - Total assets
- `DEPDOM` - Domestic deposits (institution)
- `DEPSUM` - Total deposits (institution)

### Location Data
- `ADDRESS` - Branch address
- `CITY` - City
- `STALPBR` - State abbreviation
- `ZIPBR` - ZIP code
- `SIMS_LATITUDE` - Latitude
- `SIMS_LONGITUDE` - Longitude
- `CBSA` - Core Based Statistical Area code
- `MSA` - Metropolitan Statistical Area

### Branch Type
- `BKMO` - Main office indicator (1 = yes, 0 = no)
- `BRSERTYP` - Service type code
- `CONSOLD` - Consolidated reporting branch

### Holding Company
- `RSSDHCR` - RSSD ID of bank holding company
- `NAMEHCR` - BHC name
- `HCTMULT` - Holding company type

**Full field list**: https://api.fdic.gov/banks/docs/sod_properties.yaml

## Example API Calls

### Get all 2025 data (first 10,000 records)
```
https://api.fdic.gov/banks/v1/sod?filters=YEAR:2025&limit=10000&offset=0
```

### Get specific institution by FDIC Cert
```
https://api.fdic.gov/banks/v1/sod?filters=CERT:3511 AND YEAR:2025&limit=1000
```

### Get specific fields only
```
https://api.fdic.gov/banks/v1/sod?filters=YEAR:2025&fields=CERT,RSSDID,NAMEFULL,DEPSUMBR,BKMO&limit=10000
```

### Get data for multiple years
```
# 2024
https://api.fdic.gov/banks/v1/sod?filters=YEAR:2024&limit=10000&offset=0

# 2023
https://api.fdic.gov/banks/v1/sod?filters=YEAR:2023&limit=10000&offset=0
```

### Get CSV format instead of JSON
```
https://api.fdic.gov/banks/v1/sod?filters=YEAR:2025&limit=10000&format=csv
```

## Using the API in Python

### Our Download Script

We've created `download_sod_data_api.py` that handles all the complexity:

```bash
# Download all available years
python download_sod_data_api.py --start-year 1994 --end-year 2025

# Download recent years only
python download_sod_data_api.py --start-year 2020 --end-year 2025

# Download with verbose logging
python download_sod_data_api.py --start-year 2025 --end-year 2025 --verbose
```

### Manual API Usage

If you want to use the API directly:

```python
import requests
import pandas as pd

def get_sod_data(year, limit=10000, offset=0):
    """Get SOD data for a specific year."""
    url = "https://api.fdic.gov/banks/v1/sod"

    params = {
        'filters': f'YEAR:{year}',
        'limit': limit,
        'offset': offset,
        'sort_by': 'CERT',
        'sort_order': 'ASC'
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    records = data['data']
    total = data['meta']['total']

    return pd.DataFrame(records), total

# Example: Get 2025 data
df, total = get_sod_data(2025)
print(f"Retrieved {len(df)} of {total} total records")
print(df.head())
```

### Pagination Example

Since the API limits to 10,000 records per request, you need to paginate:

```python
def get_all_sod_data(year):
    """Get all SOD data for a year using pagination."""
    all_data = []
    offset = 0
    limit = 10000

    while True:
        df, total = get_sod_data(year, limit=limit, offset=offset)

        if len(df) == 0:
            break

        all_data.append(df)
        offset += len(df)

        print(f"Downloaded {offset} / {total} records")

        if offset >= total:
            break

    return pd.concat(all_data, ignore_index=True)

# Get all 2025 data
df_2025 = get_all_sod_data(2025)
print(f"Total records: {len(df_2025)}")
```

## Filtering Examples

### By State
```
filters=STALPBR:"NY" AND YEAR:2025
```

### By Institution
```
filters=NAMEFULL:"JPMorgan Chase" AND YEAR:2025
```

### By Deposit Size
```
filters=DEPSUMBR:[10000 TO *] AND YEAR:2025
```
(Branches with deposits >= $10M)

### Main Offices Only
```
filters=BKMO:1 AND YEAR:2025
```

### Date Range
```
filters=YEAR:[2020 TO 2025]
```

### Multiple Conditions
```
filters=STALPBR:"CA" AND YEAR:2025 AND BKMO:0
```
(California branches that are NOT main offices)

## Rate Limits

The API documentation doesn't specify hard rate limits, but to be respectful:

- **Recommended delay**: 0.5-1 second between requests
- **Max records per request**: 10,000
- **Our script default**: 0.5 second delay

## Error Handling

Common HTTP status codes:

- **200**: Success
- **400**: Bad request (invalid parameters)
- **429**: Too many requests (rate limited)
- **500**: Server error (retry)

Our download script includes automatic retry logic for 500-level errors.

## Data Freshness

SOD data is collected annually as of **June 30** each year and typically available a few months later:

- June 30, 2025 data → Available by September 2025
- June 30, 2024 data → Available now
- Historical data back to 1987 → All available

## Complete Pipeline Using API

### Quick Start
```bash
# Set API key (one-time setup)
set FDIC_API_KEY=NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K

# One command to download and process all available years (1994-2025)
python run_sod_pipeline_api.py --start-year 1994 --end-year 2025
```

Or with API key as argument:
```bash
python run_sod_pipeline_api.py --start-year 1994 --end-year 2025 --api-key NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K
```

### Step by Step
```bash
# Step 1: Download via API (1994-2025, ~15-20 minutes)
set FDIC_API_KEY=NXHnC7gfTtGewKftjNxLMnPuCRd9EHfm57v6xK4K
python download_sod_data_api.py --start-year 1994 --end-year 2025 --output-dir ../data/sod/raw

# Step 2: Import and clean (~5-10 minutes)
python import_clean_sod_data.py --input-dir ../data/sod/raw --output ../data/sod/sod_all_raw.parquet
```

## Comparison with Stata Code

The `imp4_sod.do` Stata script downloads ZIP files. Our Python API approach:

✅ **Replaces**: Lines 43-88 (download and unzip)
✅ **Improves**: More reliable, works for 2025+, no manual downloads
✅ **Compatible**: Same CSV format, same fields, same cleaning logic

## Additional Resources

- **API Documentation**: https://api.fdic.gov/banks/docs/
- **OpenAPI Spec**: https://api.fdic.gov/banks/docs/swagger.yaml
- **SOD Field Definitions**: https://api.fdic.gov/banks/docs/sod_properties.yaml
- **FDIC Data Portal**: https://banks.data.fdic.gov/

## Support

For API issues:
- Check FDIC API status
- Review error messages in logs
- Use `--verbose` flag for detailed debugging
- Try again later if server errors persist

For script issues:
- See [SOD_QUICKSTART.md](SOD_QUICKSTART.md)
- See [README_SOD.md](README_SOD.md)
- Check GitHub issues
