"""
View variable descriptions from SOD parquet files.

Usage:
    # List all variables with descriptions
    python describe.py data/processed/2025.parquet

    # Show description for specific variable
    python describe.py data/processed/2025.parquet DEPSUMBR

    # Search for variables by keyword
    python describe.py data/processed/2025.parquet --search deposit
"""

import argparse
import sys
from pathlib import Path
import pyarrow.parquet as pq


def get_field_descriptions(parquet_path):
    """
    Extract field descriptions from parquet file metadata.

    Args:
        parquet_path: Path to parquet file

    Returns:
        Dict mapping field names to descriptions
    """
    table = pq.read_table(parquet_path)
    descriptions = {}

    for field in table.schema:
        desc = ''
        if field.metadata:
            desc = field.metadata.get(b'description', b'').decode('utf-8')
        descriptions[field.name] = desc

    return descriptions


def main():
    parser = argparse.ArgumentParser(
        description='View variable descriptions from SOD parquet files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all variables with descriptions
  python describe.py data/processed/2025.parquet

  # Show description for specific variable
  python describe.py data/processed/2025.parquet DEPSUMBR

  # Search for variables by keyword
  python describe.py data/processed/2025.parquet --search deposit

  # Show only variables without descriptions
  python describe.py data/processed/2025.parquet --missing
        """
    )

    parser.add_argument(
        'parquet_file',
        type=str,
        help='Path to parquet file'
    )

    parser.add_argument(
        'variable',
        type=str,
        nargs='?',
        help='Specific variable to describe (optional)'
    )

    parser.add_argument(
        '--search', '-s',
        type=str,
        help='Search for variables containing keyword (case-insensitive)'
    )

    parser.add_argument(
        '--missing', '-m',
        action='store_true',
        help='Show only variables without descriptions'
    )

    args = parser.parse_args()

    # Check file exists
    parquet_path = Path(args.parquet_file)
    if not parquet_path.exists():
        print(f"ERROR: File not found: {parquet_path}")
        return 1

    # Get descriptions
    descriptions = get_field_descriptions(parquet_path)

    if not descriptions:
        print("No variables found in file")
        return 1

    # Filter based on options
    if args.variable:
        # Show specific variable
        var = args.variable.upper()
        if var in descriptions:
            desc = descriptions[var] or '(no description)'
            print(f"{var}: {desc}")
        else:
            print(f"Variable '{var}' not found")
            print(f"\nAvailable variables: {', '.join(sorted(descriptions.keys())[:10])}...")
            return 1

    elif args.search:
        # Search for keyword
        keyword = args.search.lower()
        matches = {k: v for k, v in descriptions.items()
                   if keyword in k.lower() or keyword in v.lower()}

        if not matches:
            print(f"No variables matching '{args.search}'")
            return 1

        print(f"Variables matching '{args.search}':")
        print("-" * 60)
        for name in sorted(matches.keys()):
            desc = matches[name] or '(no description)'
            print(f"{name}: {desc}")

    elif args.missing:
        # Show variables without descriptions
        missing = {k: v for k, v in descriptions.items() if not v}

        if not missing:
            print("All variables have descriptions!")
            return 0

        print(f"Variables without descriptions ({len(missing)}):")
        print("-" * 60)
        for name in sorted(missing.keys()):
            print(name)

    else:
        # Show all variables
        print(f"Variables in {parquet_path.name} ({len(descriptions)} total):")
        print("=" * 70)

        # Count variables with descriptions
        with_desc = sum(1 for v in descriptions.values() if v)
        print(f"With descriptions: {with_desc}/{len(descriptions)}")
        print("=" * 70)

        for name in sorted(descriptions.keys()):
            desc = descriptions[name] or '(no description)'
            # Truncate long descriptions
            if len(desc) > 50:
                desc = desc[:47] + '...'
            print(f"{name:25} {desc}")

    return 0


if __name__ == '__main__':
    sys.exit(main())
