import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from main import DEFAULT_DATE, get_interactive_args, main


class TestMain(unittest.TestCase):
    def test_empty_date_uses_default(self) -> None:
        with patch("builtins.input", side_effect=["", "", ""]):
            args = get_interactive_args()

        self.assertEqual(args.date, DEFAULT_DATE)
        self.assertEqual(args.data_dir, Path("data"))
        self.assertEqual(args.output_dir, Path("reports"))

    def test_invalid_interactive_date_returns_error(self) -> None:
        stderr = StringIO()

        with (
            patch("sys.argv", ["main.py"]),
            patch("builtins.input", side_effect=["", "2026-13-10", ""]),
            redirect_stderr(stderr),
        ):
            result = main()

        self.assertEqual(result, 1)
        self.assertIn("Ошибка:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
