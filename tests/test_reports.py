import sys
import tempfile
import unittest
import smtplib
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from build import parse_issue, build
from insights import summarize
from mail import periods, deliver, smtp_send
from unittest.mock import patch


def record(number=1, test=False):
    return dict(number=number, date='2026-10-11', minutes=60, topic='工具调用', category='工具调用与 MCP',
                learned='学会工具参数校验', practice='完成 demo', questions='待复查超时', next='补上重试',
                mastery='3 · 能独立实践', moments='看到了晚霞', test=test,
                url=f'https://github.com/example/log/issues/{number}')


class MemoryLedger:
    def __init__(self):
        self.state = None

    def get(self, key):
        return self.state, 'sha' if self.state else None

    def put(self, key, state, sha=None):
        self.state = dict(state)
        return 'sha'


class ReportTests(unittest.TestCase):
    def test_complete_periods(self):
        self.assertIn(('weekly', date(2025,12,29), date(2026,1,4)), periods(date(2026,1,5)))
        self.assertIn(('monthly', date(2024,2,1), date(2024,2,29)), periods(date(2024,3,1)))
        self.assertNotIn('weekly', [p[0] for p in periods(date(2026,10,11))])

    def test_test_exclusion_and_next_step(self):
        text = summarize([record(), dict(record(2,True), minutes=999, moments='TEST_ONLY')], 'daily', date(2026,10,11), date(2026,10,11))
        self.assertIn('60 分钟', text)
        self.assertIn('补上重试', text)
        self.assertNotIn('TEST_ONLY', text)
        self.assertNotIn('999', text)

    def test_legacy_and_new_fields(self):
        issue = dict(number=1, created_at='2026-10-10T16:00:00Z', html_url='https://github.com/example/log/issues/1',
                     title='[打卡] 测试打卡｜功能验收', body='### 今天学了什么\n内容\n### 今天完成了什么\n成果\n### 掌握程度\n3 · 能独立实践\n### 今日拾光\n小事')
        parsed = parse_issue(issue)
        self.assertTrue(parsed['test'])
        self.assertEqual(parsed['minutes'], 0)
        self.assertEqual(parsed['practice'], '成果')
        issue['title'] = '[打卡] 正式'
        issue['body'] += '\n### 记录类型\n测试记录（不计入统计和正式邮件）'
        self.assertTrue(parse_issue(issue)['test'])

    def test_views_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as tmp:
            root = Path(tmp)
            build(root, [record(), record(2,True)], today=date(2026,10,11))
            self.assertIn('1 次打卡', (root/'README.md').read_text(encoding='utf-8'))
            self.assertIn('看到了晚霞', (root/'views/moments.md').read_text(encoding='utf-8'))
            self.assertIn('不计入', (root/'views/testing.md').read_text(encoding='utf-8'))
            self.assertTrue((root/'views/assets/heatmap.svg').exists())
            self.assertIn('补上重试', (root/'views/summaries/week-2026-W41.md').read_text(encoding='utf-8'))
            build(root, [record(2,True)], today=date(2026,10,11))
            self.assertFalse((root/'views/summaries/week-2026-W41.md').exists())
            self.assertIn('0 次打卡', (root/'README.md').read_text(encoding='utf-8'))

    def test_deduplication_and_ambiguous_failure(self):
        ledger = MemoryLedger()
        sent = []
        cfg = dict(SMTP_USERNAME='sender@example.com', SMTP_PASSWORD='not-a-real-secret', MAIL_TO='dest@example.com')
        args = ('daily', date(2026,10,11), date(2026,10,11), 'test', cfg, ledger)
        self.assertEqual(deliver(*args, send=lambda *a: sent.append(1)), 'sent')
        self.assertEqual(deliver(*args, send=lambda *a: sent.append(1)), 'skipped')
        self.assertEqual(len(sent), 1)
        ledger.state = None
        def ambiguous(*a):
            raise smtplib.SMTPServerDisconnected('no acknowledgement')
        with self.assertRaises(smtplib.SMTPServerDisconnected):
            deliver(*args, send=ambiguous)
        self.assertEqual(ledger.state['status'], 'unknown')
        self.assertEqual(deliver(*args, send=lambda *a: sent.append(1)), 'skipped')
        self.assertNotIn('dest@example.com', str(ledger.state))

    def test_safe_failure_retry_and_ambiguous_no_retry(self):
        cfg = dict(SMTP_USERNAME='sender@example.com', SMTP_PASSWORD='dummy', MAIL_TO='dest@example.com')
        with patch('mail.smtplib.SMTP_SSL', side_effect=[OSError(), OSError(), OSError()]) as smtp:
            with self.assertRaises(OSError):
                smtp_send(object(), cfg, sleep=lambda _: None)
            self.assertEqual(smtp.call_count, 3)
        with patch('mail.smtplib.SMTP_SSL') as smtp:
            smtp.return_value.send_message.side_effect = smtplib.SMTPServerDisconnected()
            with self.assertRaises(smtplib.SMTPServerDisconnected):
                smtp_send(object(), cfg, sleep=lambda _: None)
            self.assertEqual(smtp.call_count, 1)


if __name__ == '__main__':
    unittest.main()
