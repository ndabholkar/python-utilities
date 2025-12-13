"""
Video Filename Fixer
--------------------

A utility for fixing the ordering of offline video tutorial files by renaming
them with zero-padded numbers at the start of their filenames.

Many tutorial files are named with one or two digits at the beginning, followed
by a separator such as a dot (.), space, dash (-), or combinations of these.
File systems treat filenames as alphanumeric, so "10 Advanced.mp4" is ordered
before "02 - Basics.mp4", which is incorrect. This utility recursively traverses
a given folder and replaces starting digits with 3-digit zero-padded numbers.

Example:
    "1. Introduction.mp4" → "001. Introduction.mp4"
    "02 - Basics.mp4" → "002 - Basics.mp4"
    "10 Advanced.mp4" → "010 Advanced.mp4"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set, Tuple
import os
import re


PathLike = str | os.PathLike[str]


# Common video file extensions
DEFAULT_VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv', '.ts', '.vob'
}


@dataclass
class RenameResult:
    """Result of a single file rename operation."""
    original_path: Path
    new_path: Path
    success: bool
    error_message: Optional[str] = None


@dataclass
class VideoFilenameFixer:
    """
    Utility for fixing video tutorial file ordering by zero-padding numbers
    at the start of filenames.

    Attributes:
        video_extensions: Set of video file extensions to process (e.g., {'.mp4', '.avi'}).
                         Defaults to a comprehensive list of common video formats.
        padding_width: Number of digits to pad to (default: 3).
        dry_run: If True, preview changes without actually renaming files.
    """
    video_extensions: Set[str] = field(default_factory=lambda: DEFAULT_VIDEO_EXTENSIONS.copy())
    padding_width: int = 3
    dry_run: bool = False

    # Pattern to match filenames starting with 1-2 digits followed by optional separators
    # Group 1: the digits, Group 2: the rest (separators + filename)
    _filename_pattern = re.compile(r'^(\d{1,2})([.\s\-]+.*)$')

    def __post_init__(self) -> None:
        """Normalize video extensions to lowercase with leading dots."""
        self.video_extensions = {
            ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
            for ext in self.video_extensions
        }

        if self.padding_width < 1:
            raise ValueError("padding_width must be at least 1")

    def should_process_file(self, file_path: Path) -> bool:
        """
        Check if a file should be processed based on its extension.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file has a video extension, False otherwise.
        """
        return file_path.suffix.lower() in self.video_extensions

    def needs_padding(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a filename needs padding and return the new filename if so.

        Args:
            filename: The filename (not full path) to check.

        Returns:
            A tuple of (needs_padding, new_filename).
            - needs_padding: True if the filename starts with 1-2 digits
            - new_filename: The new filename with padded digits, or None if no change needed
        """
        match = self._filename_pattern.match(filename)
        if not match:
            return False, None

        digits_str, rest = match.groups()

        # Check if already properly padded
        if len(digits_str) >= self.padding_width:
            return False, None

        # Create zero-padded version
        padded_digits = digits_str.zfill(self.padding_width)
        new_filename = f"{padded_digits}{rest}"

        return True, new_filename

    def fix_file(self, file_path: Path) -> Optional[RenameResult]:
        """
        Fix a single file by renaming it with zero-padded numbers.

        Args:
            file_path: Path to the file to fix.

        Returns:
            RenameResult if the file was renamed (or would be in dry-run mode),
            None if the file doesn't need changes.
        """
        if not self.should_process_file(file_path):
            return None

        needs_fix, new_filename = self.needs_padding(file_path.name)

        if not needs_fix:
            return None

        new_path = file_path.parent / new_filename

        # Check if target already exists
        if new_path.exists() and new_path != file_path:
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=False,
                error_message=f"Target file already exists: {new_path}"
            )

        if self.dry_run:
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=True,
                error_message=None
            )

        try:
            file_path.rename(new_path)
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=True,
                error_message=None
            )
        except Exception as e:
            return RenameResult(
                original_path=file_path,
                new_path=new_path,
                success=False,
                error_message=str(e)
            )

    def fix_directory(
        self,
        directory: PathLike,
        recursive: bool = True,
        verbose: bool = True
    ) -> List[RenameResult]:
        """
        Fix all video files in a directory by renaming them with zero-padded numbers.

        Args:
            directory: Path to the directory to process.
            recursive: If True, process subdirectories recursively.
            verbose: If True, print log messages for each rename.

        Returns:
            List of RenameResult objects for all renamed files.
        """
        dir_path = Path(directory)

        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        results: List[RenameResult] = []

        # Collect all files to process
        if recursive:
            files = sorted(dir_path.rglob('*'))
        else:
            files = sorted(dir_path.glob('*'))

        # Filter to only files (not directories)
        files = [f for f in files if f.is_file()]

        # Process each file
        for file_path in files:
            result = self.fix_file(file_path)

            if result is not None:
                results.append(result)

                if verbose:
                    self._log_result(result)

        # Summary
        if verbose and results:
            self._print_summary(results)

        return results

    def _log_result(self, result: RenameResult) -> None:
        """Print a log message for a single rename result."""
        mode = "[DRY RUN] " if self.dry_run else ""

        if result.success:
            print(f"{mode}✓ {result.original_path.name} → {result.new_path.name}")
        else:
            print(f"{mode}✗ {result.original_path.name}: {result.error_message}")

    def _print_summary(self, results: List[RenameResult]) -> None:
        """Print a summary of all rename operations."""
        total = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total - successful

        print(f"\n{'=' * 60}")
        print(f"Summary:")
        print(f"  Total files processed: {total}")
        print(f"  Successful renames: {successful}")
        if failed > 0:
            print(f"  Failed renames: {failed}")

        if self.dry_run:
            print(f"\n  This was a DRY RUN. No files were actually renamed.")
        print(f"{'=' * 60}")


def fix_video_filenames(
    directory: PathLike,
    recursive: bool = True,
    dry_run: bool = False,
    verbose: bool = True,
    padding_width: int = 3,
    video_extensions: Optional[Set[str]] = None
) -> List[RenameResult]:
    """
    Convenience function to fix video tutorial filenames in a directory.

    Args:
        directory: Path to the directory to process.
        recursive: If True, process subdirectories recursively (default: True).
        dry_run: If True, preview changes without renaming files (default: False).
        verbose: If True, print log messages (default: True).
        padding_width: Number of digits to pad to (default: 3).
        video_extensions: Set of video extensions to process. If None, uses defaults.

    Returns:
        List of RenameResult objects for all renamed files.

    Example:
        >>> # Preview changes without renaming
        >>> preview = fix_video_filenames('/path/to/tutorials', dry_run=True)
        >>>
        >>> # Actually rename files
        >>> results = fix_video_filenames('/path/to/tutorials', dry_run=False)
    """
    kwargs = {'padding_width': padding_width, 'dry_run': dry_run}
    if video_extensions is not None:
        kwargs['video_extensions'] = video_extensions

    fixer = VideoFilenameFixer(**kwargs)
    return fixer.fix_directory(directory, recursive=recursive, verbose=verbose)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python video_filename_fixer.py <directory> [--dry-run] [--no-recursive]")
        print("\nOptions:")
        print("  --dry-run        Preview changes without actually renaming files")
        print("  --no-recursive   Don't process subdirectories")
        sys.exit(1)

    directory = sys.argv[1]
    dry_run = '--dry-run' in sys.argv
    recursive = '--no-recursive' not in sys.argv

    try:
        fix_video_filenames(directory, recursive=recursive, dry_run=dry_run)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

