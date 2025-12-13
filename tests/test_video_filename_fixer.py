import unittest
from pathlib import Path
import tempfile

from video_filename_fixer import (
    VideoFilenameFixer,
    fix_video_filenames,
    RenameResult,
    DEFAULT_VIDEO_EXTENSIONS
)


class VideoFilenameFixerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.base = Path(self.td.name)

    def create_test_file(self, relative_path: str) -> Path:
        """Helper to create a test file."""
        full_path = self.base / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.touch()
        return full_path

    def test_should_process_file_with_video_extensions(self):
        fixer = VideoFilenameFixer()

        # Should process common video formats
        self.assertTrue(fixer.should_process_file(Path("video.mp4")))
        self.assertTrue(fixer.should_process_file(Path("video.avi")))
        self.assertTrue(fixer.should_process_file(Path("video.mkv")))
        self.assertTrue(fixer.should_process_file(Path("video.mov")))

        # Should not process non-video files
        self.assertFalse(fixer.should_process_file(Path("document.txt")))
        self.assertFalse(fixer.should_process_file(Path("image.jpg")))
        self.assertFalse(fixer.should_process_file(Path("archive.zip")))

    def test_should_process_file_case_insensitive(self):
        fixer = VideoFilenameFixer()

        # Extensions should be case-insensitive
        self.assertTrue(fixer.should_process_file(Path("video.MP4")))
        self.assertTrue(fixer.should_process_file(Path("video.Mkv")))
        self.assertTrue(fixer.should_process_file(Path("video.AVI")))

    def test_custom_video_extensions(self):
        fixer = VideoFilenameFixer(video_extensions={'.custom', '.test'})

        self.assertTrue(fixer.should_process_file(Path("file.custom")))
        self.assertTrue(fixer.should_process_file(Path("file.test")))
        self.assertFalse(fixer.should_process_file(Path("file.mp4")))

    def test_needs_padding_single_digit_with_dot(self):
        fixer = VideoFilenameFixer()

        needs, new_name = fixer.needs_padding("1. Introduction.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "001. Introduction.mp4")

    def test_needs_padding_single_digit_with_space(self):
        fixer = VideoFilenameFixer()

        needs, new_name = fixer.needs_padding("5 Basics.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "005 Basics.mp4")

    def test_needs_padding_single_digit_with_dash(self):
        fixer = VideoFilenameFixer()

        needs, new_name = fixer.needs_padding("3 - Advanced.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "003 - Advanced.mp4")

    def test_needs_padding_two_digits(self):
        fixer = VideoFilenameFixer()

        needs, new_name = fixer.needs_padding("42. Chapter Forty Two.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "042. Chapter Forty Two.mp4")

    def test_needs_padding_mixed_separators(self):
        fixer = VideoFilenameFixer()

        needs, new_name = fixer.needs_padding("7 .- Test.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "007 .- Test.mp4")

    def test_needs_padding_already_padded(self):
        fixer = VideoFilenameFixer()

        # Already 3 digits, should not need padding
        needs, new_name = fixer.needs_padding("001. Introduction.mp4")
        self.assertFalse(needs)
        self.assertIsNone(new_name)

        # More than 3 digits, should not need padding
        needs, new_name = fixer.needs_padding("1234. Introduction.mp4")
        self.assertFalse(needs)
        self.assertIsNone(new_name)

    def test_needs_padding_no_digits_at_start(self):
        fixer = VideoFilenameFixer()

        # No digits at start
        needs, new_name = fixer.needs_padding("Introduction.mp4")
        self.assertFalse(needs)
        self.assertIsNone(new_name)

        # Digits in middle
        needs, new_name = fixer.needs_padding("Chapter 1 - Intro.mp4")
        self.assertFalse(needs)
        self.assertIsNone(new_name)

    def test_needs_padding_no_separator(self):
        fixer = VideoFilenameFixer()

        # Digits without separator shouldn't match
        needs, new_name = fixer.needs_padding("1Introduction.mp4")
        self.assertFalse(needs)
        self.assertIsNone(new_name)

    def test_custom_padding_width(self):
        fixer = VideoFilenameFixer(padding_width=4)

        needs, new_name = fixer.needs_padding("5. Test.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "0005. Test.mp4")

        # Two digits should still be padded
        needs, new_name = fixer.needs_padding("42. Test.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "0042. Test.mp4")

    def test_fix_file_renames_correctly(self):
        fixer = VideoFilenameFixer(dry_run=False)

        # Create a test file
        test_file = self.create_test_file("1. Introduction.mp4")

        result = fixer.fix_file(test_file)

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.original_path, test_file)
        self.assertEqual(result.new_path.name, "001. Introduction.mp4")
        self.assertTrue(result.new_path.exists())
        self.assertFalse(test_file.exists())

    def test_fix_file_dry_run(self):
        fixer = VideoFilenameFixer(dry_run=True)

        test_file = self.create_test_file("2. Chapter Two.mp4")

        result = fixer.fix_file(test_file)

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.new_path.name, "002. Chapter Two.mp4")
        # Original file should still exist in dry run mode
        self.assertTrue(test_file.exists())
        self.assertFalse(result.new_path.exists())

    def test_fix_file_skips_non_video_files(self):
        fixer = VideoFilenameFixer(dry_run=False)

        test_file = self.create_test_file("1. Document.txt")

        result = fixer.fix_file(test_file)

        self.assertIsNone(result)
        self.assertTrue(test_file.exists())

    def test_fix_file_skips_files_without_digits(self):
        fixer = VideoFilenameFixer(dry_run=False)

        test_file = self.create_test_file("Introduction.mp4")

        result = fixer.fix_file(test_file)

        self.assertIsNone(result)
        self.assertTrue(test_file.exists())

    def test_fix_file_target_already_exists(self):
        fixer = VideoFilenameFixer(dry_run=False)

        # Create both original and target files
        test_file = self.create_test_file("1. Intro.mp4")
        target_file = self.create_test_file("001. Intro.mp4")

        result = fixer.fix_file(test_file)

        self.assertIsNotNone(result)
        self.assertFalse(result.success)
        self.assertIn("already exists", result.error_message)
        # Both files should still exist
        self.assertTrue(test_file.exists())
        self.assertTrue(target_file.exists())

    def test_fix_directory_non_recursive(self):
        fixer = VideoFilenameFixer(dry_run=False)

        # Create files in root and subdirectory
        root_file = self.create_test_file("1. Root.mp4")
        sub_file = self.create_test_file("subdir/2. Sub.mp4")

        results = fixer.fix_directory(self.base, recursive=False, verbose=False)

        # Only root file should be renamed
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].original_path, root_file)
        self.assertTrue((self.base / "001. Root.mp4").exists())
        # Subdirectory file should remain unchanged
        self.assertTrue(sub_file.exists())

    def test_fix_directory_recursive(self):
        fixer = VideoFilenameFixer(dry_run=False)

        # Create files in multiple levels
        file1 = self.create_test_file("1. Root.mp4")
        file2 = self.create_test_file("subdir/2. Sub.mp4")
        file3 = self.create_test_file("subdir/nested/3. Nested.mp4")

        results = fixer.fix_directory(self.base, recursive=True, verbose=False)

        # All files should be renamed
        self.assertEqual(len(results), 3)
        self.assertTrue((self.base / "001. Root.mp4").exists())
        self.assertTrue((self.base / "subdir" / "002. Sub.mp4").exists())
        self.assertTrue((self.base / "subdir" / "nested" / "003. Nested.mp4").exists())

    def test_fix_directory_mixed_files(self):
        fixer = VideoFilenameFixer(dry_run=False)

        # Create mix of files that need and don't need renaming
        self.create_test_file("1. Needs padding.mp4")
        self.create_test_file("001. Already padded.mp4")
        self.create_test_file("No digits.mp4")
        self.create_test_file("1. Text file.txt")
        self.create_test_file("42. Also needs.avi")

        results = fixer.fix_directory(self.base, recursive=False, verbose=False)

        # Only files that need padding (and are videos) should be renamed
        self.assertEqual(len(results), 2)
        self.assertTrue((self.base / "001. Needs padding.mp4").exists())
        self.assertTrue((self.base / "042. Also needs.avi").exists())

    def test_fix_directory_not_found(self):
        fixer = VideoFilenameFixer()

        with self.assertRaises(FileNotFoundError):
            fixer.fix_directory("/nonexistent/directory")

    def test_fix_directory_not_a_directory(self):
        fixer = VideoFilenameFixer()

        # Create a file instead of directory
        test_file = self.create_test_file("somefile.txt")

        with self.assertRaises(NotADirectoryError):
            fixer.fix_directory(test_file)

    def test_convenience_function(self):
        # Test the convenience function
        self.create_test_file("5. Test.mp4")
        self.create_test_file("12. Another.mp4")

        results = fix_video_filenames(
            self.base,
            recursive=False,
            dry_run=False,
            verbose=False
        )

        self.assertEqual(len(results), 2)
        self.assertTrue((self.base / "005. Test.mp4").exists())
        self.assertTrue((self.base / "012. Another.mp4").exists())

    def test_convenience_function_with_custom_padding(self):
        self.create_test_file("3. Test.mp4")

        results = fix_video_filenames(
            self.base,
            padding_width=5,
            verbose=False
        )

        self.assertEqual(len(results), 1)
        self.assertTrue((self.base / "00003. Test.mp4").exists())

    def test_convenience_function_with_custom_extensions(self):
        self.create_test_file("1. Video.mp4")
        self.create_test_file("2. Custom.xyz")

        # Only process .xyz files
        results = fix_video_filenames(
            self.base,
            video_extensions={'.xyz'},
            verbose=False
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].new_path.name, "002. Custom.xyz")
        # .mp4 file should not be renamed
        self.assertTrue((self.base / "1. Video.mp4").exists())

    def test_rename_result_dataclass(self):
        original = Path("/test/1. Original.mp4")
        new = Path("/test/001. Original.mp4")

        # Success case
        result = RenameResult(
            original_path=original,
            new_path=new,
            success=True
        )

        self.assertEqual(result.original_path, original)
        self.assertEqual(result.new_path, new)
        self.assertTrue(result.success)
        self.assertIsNone(result.error_message)

        # Failure case
        result_fail = RenameResult(
            original_path=original,
            new_path=new,
            success=False,
            error_message="Permission denied"
        )

        self.assertFalse(result_fail.success)
        self.assertEqual(result_fail.error_message, "Permission denied")

    def test_default_video_extensions_comprehensive(self):
        # Verify DEFAULT_VIDEO_EXTENSIONS includes common formats
        expected_formats = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv'}
        self.assertTrue(expected_formats.issubset(DEFAULT_VIDEO_EXTENSIONS))

    def test_invalid_padding_width(self):
        with self.assertRaises(ValueError):
            VideoFilenameFixer(padding_width=0)

        with self.assertRaises(ValueError):
            VideoFilenameFixer(padding_width=-1)

    def test_complex_filename_patterns(self):
        fixer = VideoFilenameFixer()

        # Test various complex patterns
        test_cases = [
            ("1. Introduction to Python.mp4", "001. Introduction to Python.mp4"),
            ("02 - Object Oriented Programming.avi", "002 - Object Oriented Programming.avi"),
            ("9.   Extra Spaces.mkv", "009.   Extra Spaces.mkv"),
            ("15 -- Double Dash.mov", "015 -- Double Dash.mov"),
            ("7. File with (parentheses) [brackets].mp4", "007. File with (parentheses) [brackets].mp4"),
            ("99. Special chars @#$%.mp4", "099. Special chars @#$%.mp4"),
        ]

        for original, expected in test_cases:
            needs, new_name = fixer.needs_padding(original)
            self.assertTrue(needs, f"Should need padding: {original}")
            self.assertEqual(new_name, expected, f"Wrong padding for: {original}")

    def test_edge_case_filenames(self):
        fixer = VideoFilenameFixer()

        # Test edge cases that should NOT be renamed
        no_rename_cases = [
            "100. Already three digits.mp4",
            "1000. Four digits.mp4",
            "Introduction 1.mp4",  # Digits not at start
            "Chapter1.mp4",  # No separator
            "1",  # Just a digit, no extension or separator
        ]

        for filename in no_rename_cases:
            needs, new_name = fixer.needs_padding(filename)
            self.assertFalse(needs, f"Should NOT need padding: {filename}")
            self.assertIsNone(new_name)

        # Test edge case that SHOULD be renamed
        # "1.mp4" should become "001.mp4" because the dot is a valid separator
        needs, new_name = fixer.needs_padding("1.mp4")
        self.assertTrue(needs)
        self.assertEqual(new_name, "001.mp4")


if __name__ == '__main__':
    unittest.main()

