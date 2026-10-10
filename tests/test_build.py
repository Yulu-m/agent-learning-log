import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path

spec = importlib.util.spec_from_file_location('build', Path(__file__).resolve().parents[1] / 'scripts/build.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CheckinTests(unittest.TestCase):
    def issue(self, day='', minutes='60'):
        return dict(number=1, html_url='https://github.com/example/log/issues/1', created_at='2026-10-09T17:00:00Z',
                    body=f'### 学习日期\n\n{day or "_No response_"}\n\n### 学习主题\n\nMCP\n\n### 学习时长（分钟）\n\n{minutes}\n\n### 今天学了什么\n\n工具调用\n')

    def test_beijing_default(self):
        self.assertEqual(module.parse_issue(self.issue())['date'], '2026-10-10')
        self.assertEqual(module.parse_issue(self.issue('提交当天（北京时间）'))['date'], '2026-10-10')

    def test_invalid_input(self):
        for d, m in [('2026-02-30', '60'), ('26-1-2', '60'), ('2026-10-10', '-1'), ('2026-10-10', '1441'), ('2026-10-10', '1; echo secret')]:
            with self.assertRaises(ValueError):
                module.parse_issue(self.issue(d, m))

    def test_duplicate_day_and_cross_year(self):
        a = module.parse_issue(self.issue('2021-01-01'))
        b = dict(a, number=2, minutes=30)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as tmp:
            root = Path(tmp)
            module.build(root, [a, b], today=date(2026, 10, 10))
            self.assertIn('2020-W53', (root / 'views/weekly.md').read_text(encoding='utf-8'))
            self.assertIn('1 天** · **2 次打卡** · **90 分钟', (root / 'README.md').read_text(encoding='utf-8'))
            self.assertIn('(90)', (root / 'views/monthly.md').read_text(encoding='utf-8'))
            module.build(root, [dict(a, date='2021-01-02')], today=date(2026, 10, 10))
            self.assertFalse((root / 'views/days/2021-01-01.md').exists())

    def test_empty_and_safe_text(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as tmp:
            root = Path(tmp)
            module.build(root, [], today=date(2026, 10, 10))
            self.assertIn('0 次打卡', (root / 'README.md').read_text(encoding='utf-8'))
            self.assertIn('## 2026-10', (root / 'views/monthly.md').read_text(encoding='utf-8'))
        self.assertNotIn('<script>', module.safe('<script>alert(1)</script>|[x]'))


if __name__ == '__main__':
    unittest.main()
