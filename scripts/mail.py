"""Scheduled reports via Gmail SMTP. Credentials live only in Actions Secrets."""
import argparse
import calendar
import html
import json
import os
import smtplib
import ssl
import time
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from base64 import b64encode

from insights import formal, summarize

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))


def periods(today, kind='auto'):
    result = [('daily', today-timedelta(days=1), today-timedelta(days=1))]
    if today.weekday() == 0 or kind == 'weekly':
        monday = today - timedelta(days=today.weekday())
        result.append(('weekly', monday-timedelta(days=7), monday-timedelta(days=1)))
    if today.day == 1 or kind == 'monthly':
        end = today.replace(day=1)-timedelta(days=1)
        result.append(('monthly', end.replace(day=1), end))
    if kind == 'test':
        return [('test', today, today)]
    return result if kind == 'auto' else [x for x in result if x[0] == kind]


def report_key(kind, start, end):
    return f'{kind}-{start}-{end}'


def subject(kind, start, end):
    label = {'daily': '日报', 'weekly': '周报', 'monthly': '月报', 'test': '测试邮件'}[kind]
    period = start.strftime('%Y-%m') if kind == 'monthly' else str(start) if start == end else f'{start}—{end}'
    return f'Agent 学习{label}｜{period}'


class GitHubLedger:
    def __init__(self):
        self.repo = os.environ['GITHUB_REPOSITORY']
        self.token = os.environ['GITHUB_TOKEN']

    def request(self, key, body=None):
        req = Request(f'https://api.github.com/repos/{self.repo}/contents/delivery/{key}.json',
                      data=json.dumps(body).encode() if body else None,
                      headers={'Authorization': 'Bearer '+self.token, 'Accept': 'application/vnd.github+json', 'User-Agent': 'agent-learning-reports'},
                      method='PUT' if body else 'GET')
        with urlopen(req, timeout=30) as response:
            return json.load(response)

    def get(self, key):
        from base64 import b64decode
        try:
            result = self.request(key)
            return json.loads(b64decode(result['content'])), result['sha']
        except HTTPError as error:
            if error.code == 404:
                return None, None
            raise

    def put(self, key, state, sha=None):
        body = dict(message=f'邮件发送日志：{key} {state["status"]}',
                    content=b64encode((json.dumps(state, ensure_ascii=False, indent=2)+'\n').encode()).decode())
        if sha:
            body['sha'] = sha
        return self.request(key, body)['content']['sha']


def config():
    values = {k: os.environ.get(k, '').strip() for k in ['SMTP_USERNAME', 'SMTP_PASSWORD', 'MAIL_TO']}
    if not all(values.values()):
        return None
    for key in ['SMTP_USERNAME', 'MAIL_TO']:
        addr = values[key]
        if '\r' in addr or '\n' in addr or parseaddr(addr)[1] != addr or '@' not in addr:
            raise ValueError('Invalid email configuration')
    return values


def smtp_send(message, cfg, sleep=time.sleep):
    """Retry safe failures only; lost acknowledgement is deliberately not retried."""
    for attempt in range(3):
        server = None
        sending = False
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465, context=ssl.create_default_context(), timeout=30)
            server.login(cfg['SMTP_USERNAME'], cfg['SMTP_PASSWORD'])
            sending = True
            refused = server.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
            return
        except smtplib.SMTPAuthenticationError:
            raise
        except smtplib.SMTPDataError as error:
            if not 400 <= error.smtp_code < 500 or attempt == 2:
                raise
        except (OSError, smtplib.SMTPServerDisconnected):
            if sending or attempt == 2:
                raise
        finally:
            if server:
                server.close()
        sleep(2 ** attempt)


def deliver(kind, start, end, text, cfg, ledger, send=smtp_send):
    key = report_key(kind, start, end)
    previous, sha = ledger.get(key)
    if previous and previous['status'] in ['sent', 'pending', 'unknown']:
        print(f'{key}: skipped ({previous["status"]})')
        return 'skipped'
    stamp = datetime.now(TZ).isoformat()
    state = {'kind': kind, 'start': str(start), 'end': str(end), 'status': 'pending', 'updated_at': stamp}
    # Commit a durable claim before contacting SMTP; an interrupted delivery is not duplicated.
    sha = ledger.put(key, state, sha)
    msg = EmailMessage()
    msg['Subject'] = subject(kind, start, end)
    msg['From'], msg['To'] = cfg['SMTP_USERNAME'], cfg['MAIL_TO']
    msg['Message-ID'] = f'<agent-learning-{key}@github-reports.local>'
    msg.set_content(text)
    msg.add_alternative('<html><body><pre style="white-space:pre-wrap;font-family:system-ui;line-height:1.7">'+html.escape(text)+'</pre></body></html>', subtype='html')
    try:
        send(msg, cfg)
    except (smtplib.SMTPAuthenticationError, smtplib.SMTPDataError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused) as error:
        state.update(status='failed', error_type=type(error).__name__)
        ledger.put(key, state, sha)
        raise
    except Exception as error:
        state.update(status='unknown', error_type=type(error).__name__)
        ledger.put(key, state, sha)
        raise
    state.update(status='sent', updated_at=datetime.now(TZ).isoformat())
    ledger.put(key, state, sha)
    print(f'{key}: sent')
    return 'sent'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=['auto', 'daily', 'weekly', 'monthly', 'test'], default='auto')
    parser.add_argument('--date', type=date.fromisoformat, help='Report execution date in Beijing time')
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    today = args.date or datetime.now(TZ).date()
    if args.date and not args.preview:
        raise ValueError('--date is only supported for preview, to prevent accidental historical sends')
    records = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'records').glob('*.json')]
    cfg = None if args.preview else config()
    out = ROOT/'mail-preview'
    out.mkdir(exist_ok=True)
    failed = False
    for kind, start, end in periods(today, args.kind):
        text = ('# Agent 学习测试邮件\n\n用于验证 GitHub 独立发件，不计入学习统计。\n\n' + summarize(records, 'daily', start, end)) if kind == 'test' else summarize(records, kind, start, end)
        (out / f'{report_key(kind,start,end)}.md').write_text(text, encoding='utf-8')
        if not cfg:
            print(f'{kind}: preview only; SMTP secrets not configured or --preview requested')
            continue
        try:
            deliver(kind, start, end, text, cfg, GitHubLedger())
        except Exception as error:
            # Never print exception details: SMTP messages can contain email addresses.
            print(f'{kind}: delivery failed ({type(error).__name__}); see delivery ledger')
            failed = True
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
