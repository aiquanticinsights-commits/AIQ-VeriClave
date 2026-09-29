"""Unit tests for lint-log fault localization (pure, no tools)."""
import unittest

from localize import format_suspects, localize, parse_diagnostics

LOG = """%Error-UNDECLARED: /tmp/x/m.sv:2:12: Undeclared identifier 'b'
    2 | assign y = a & b;
      |                ^
%Error-WIDTH: /tmp/x/m.sv:3:14: Too many digits for 4 bit number: '4'b11111'
%Warning-UNUSED: /tmp/x/m.sv:1:20: Signal is not used: 'a'
%Error: Exiting due to 2 error(s)
"""


class TestParse(unittest.TestCase):
    def test_kinds_and_locs(self):
        ds = parse_diagnostics(LOG)
        self.assertEqual(len(ds), 3)  # exit-noise line is not a diagnostic
        self.assertEqual(ds[0]["code"], "%Error-UNDECLARED")
        self.assertEqual(ds[0]["line"], 2)
        self.assertEqual(ds[2]["kind"], "warning")

    def test_empty(self):
        self.assertEqual(parse_diagnostics("all clean\n"), [])


class TestLocalize(unittest.TestCase):
    def test_located_errors_first(self):
        ss = localize("module m;\nendmodule\n", LOG)
        self.assertEqual(ss[0]["where"], "/tmp/x/m.sv:2")
        self.assertIn("UNDECLARED", ss[0]["reason"])
        self.assertEqual([s["rank"] for s in ss], [1, 2, 3])

    def test_warnings_only_when_no_errors(self):
        ss = localize("", "%Warning-UNUSED: f.sv:1:1: Signal is not used: 'a'")
        self.assertEqual(ss[0]["where"], "f.sv:1")  # location outranks signal
        self.assertTrue(any(s["signal"] == "a" for s in ss))

    def test_empty_log_no_suspects(self):
        self.assertEqual(localize("", ""), [])

    def test_top_n_cap(self):
        self.assertLessEqual(len(localize("", LOG, top_n=2)), 2)

    def test_format(self):
        ss = localize("", LOG)
        text = format_suspects(ss)
        self.assertIn("rank 1 first", text)
        self.assertIn("/tmp/x/m.sv:2", text)
        self.assertEqual(format_suspects([]), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
