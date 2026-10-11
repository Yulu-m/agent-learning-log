import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from mail import enabled_kinds


class MailSwitchTests(unittest.TestCase):
    def test_defaults_and_independent_switches(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            root = Path(folder)
            self.assertEqual(enabled_kinds(root), dict(daily=True, weekly=True, monthly=True))
            (root/'config').mkdir()
            path = root/'config/mail-settings.json'
            for d in (False, True):
                for w in (False, True):
                    for m in (False, True):
                        expected = dict(daily=d, weekly=w, monthly=m)
                        path.write_text(json.dumps(expected), encoding='utf-8')
                        self.assertEqual(enabled_kinds(root), expected)

    def test_invalid_settings_fail_closed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            root = Path(folder)
            (root/'config').mkdir()
            for invalid in [dict(daily='false', weekly=True, monthly=True), dict(daily=False), {}]:
                (root/'config/mail-settings.json').write_text(json.dumps(invalid), encoding='utf-8')
                with self.assertRaises(ValueError):
                    enabled_kinds(root)
