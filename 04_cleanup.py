"""
Clean up downloaded and processed SOD data files.

Usage:
    # Delete raw files (ZIP/CSV)
    python cleanup.py --raw

    # Delete processed files (parquet)
    python cleanup.py --processed

    # Delete everything
    python cleanup.py --all

    # Dry run (show what would be deleted)
    python cleanup.py --raw --dry-run
"""

import argparse
import sys
from pathlib import Path


def get_files(directory, patterns):
    """Get all files matching patterns in directory."""
    files = []
    dir_path = Path(directory)

    if not dir_path.exists():
        return files

    for pattern in patterns:
        files.extend(dir_path.glob(pattern))

    return sorted(files)


def delete_files(files, dry_run=False):
    """Delete files and return count."""
    deleted = 0
    total_size = 0

    for f in files:
        size = f.stat().st_size
        total_size += size

        if dry_run:
            print(f"  [DRY RUN] Would delete: {f.name} ({size / 1024 / 1024:.1f} MB)")
        else:
            f.unlink()
            print(f"  Deleted: {f.name} ({size / 1024 / 1024:.1f} MB)")
        deleted += 1

    return deleted, total_size


def main():
    parser = argparse.ArgumentParser(
        description='Clean up SOD data files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Delete raw files (ZIP/CSV)
  python cleanup.py --raw

  # Delete processed files (parquet)
  python cleanup.py --processed

  # Delete everything
  python cleanup.py --all

  # Dry run (show what would be deleted)
  python cleanup.py --all --dry-run
        """
    )

    parser.add_argument(
        '--raw',
        action='store_true',
        help='Delete raw files (ZIP/CSV) in data/raw'
    )

    parser.add_argument(
        '--processed',
        action='store_true',
        help='Delete processed files (parquet) in data/processed'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Delete all data files (raw + processed)'
    )

    parser.add_argument(
        '--raw-dir',
        type=str,
        default='data/raw',
        help='Raw data directory (default: data/raw)'
    )

    parser.add_argument(
        '--processed-dir',
        type=str,
        default='data/processed',
        help='Processed data directory (default: data/processed)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    args = parser.parse_args()

    # Handle --all flag
    if args.all:
        args.raw = True
        args.processed = True

    # Check if any action specified
    if not args.raw and not args.processed:
        print("ERROR: Specify --raw, --processed, or --all")
        parser.print_help()
        return 1

    print("=" * 60)
    print("SOD DATA CLEANUP")
    print("=" * 60)

    if args.dry_run:
        print("MODE: Dry run (no files will be deleted)")

    print()

    total_deleted = 0
    total_size = 0

    # Clean raw files
    if args.raw:
        print(f"Raw directory: {args.raw_dir}")
        raw_patterns = ['*.zip', '*.ZIP', '*.csv', '*.CSV']
        raw_files = get_files(args.raw_dir, raw_patterns)

        if raw_files:
            deleted, size = delete_files(raw_files, args.dry_run)
            total_deleted += deleted
            total_size += size
            print(f"  Total: {deleted} files ({size / 1024 / 1024:.1f} MB)")
        else:
            print("  No raw files found")
        print()

    # Clean processed files
    if args.processed:
        print(f"Processed directory: {args.processed_dir}")
        processed_patterns = ['*.parquet']
        processed_files = get_files(args.processed_dir, processed_patterns)

        if processed_files:
            deleted, size = delete_files(processed_files, args.dry_run)
            total_deleted += deleted
            total_size += size
            print(f"  Total: {deleted} files ({size / 1024 / 1024:.1f} MB)")
        else:
            print("  No processed files found")
        print()

    # Summary
    print("=" * 60)
    action = "Would delete" if args.dry_run else "Deleted"
    print(f"{action}: {total_deleted} files ({total_size / 1024 / 1024:.1f} MB)")
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(main())
