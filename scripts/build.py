"""Owner's GitHub Issues -> daily, ISO-week and calendar views. No dependencies."""
import argparse
import calendar
import html
import json
import os
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LABELS = ['学习日期', '学习主题', '学习时长（分钟）', '今天学了什么', '实践与产出', '问题与收获', '下一步', '今日拾光']
TZ = timezone(timedelta(hours=8))


def parse_issue(issue):
    body = issue.get('body') or ''
    pattern = r'^### (' + '|'.join(map(re.escape, LABELS)) + r')\s*$'
    matches = list(re.finditer(pattern, body, re.M))
    fields = {}
    for i, match in enumerate(matches):
        key = match.group(1)
        if key in fields:
            raise ValueError('表单字段重复：' + key)
        value = body[match.end():matches[i+1].start() if i+1 < len(matches) else len(body)].strip()
        fields[key] = '' if value == '_No response_' else value
    selected = fields.get(LABELS[0], '')
    day = ('' if selected == '提交当天（北京时间）' else selected) or datetime.fromisoformat(issue['created_at'].replace('Z', '+00:00')).astimezone(TZ).date().isoformat()
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
        raise ValueError('学习日期应为 YYYY-MM-DD')
    date.fromisoformat(day)
    minutes = fields.get(LABELS[2], '')
    if not re.fullmatch(r'\d{1,4}', minutes) or not 0 <= int(minutes) <= 1440:
        raise ValueError('学习时长应为 0—1440 的整数分钟')
    if not fields.get(LABELS[1]) or not fields.get(LABELS[3]):
        raise ValueError('请填写学习主题和今天学了什么')
    return dict(number=issue['number'], url=issue['html_url'], date=day,
                minutes=int(minutes), topic=fields[LABELS[1]],
                learned=fields[LABELS[3]], practice=fields.get(LABELS[4], ''),
                questions=fields.get(LABELS[5], ''), next=fields.get(LABELS[6], ''), moments=fields.get(LABELS[7], ''))


def sync(root, repo):
    owner = repo.split('/')[0]
    issues = []
    page = 1
    while True:
        request = Request(f'https://api.github.com/repos/{repo}/issues?state=all&per_page=100&page={page}',
                          headers={'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
                                   'Accept': 'application/vnd.github+json', 'User-Agent': 'agent-learning-log'})
        with urlopen(request, timeout=30) as response:
            batch = json.load(response)
        issues.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    records, errors = [], []
    for issue in issues:
        if 'pull_request' in issue or issue['user']['login'].lower() != owner.lower() or not issue['title'].startswith('[打卡]'):
            continue
        try:
            records.append(parse_issue(issue))
        except (ValueError, KeyError) as error:
            errors.append(f"- [打卡 #{issue['number']}]({issue['html_url']})：{error}")
    folder = root / 'records'
    folder.mkdir(exist_ok=True)
    # Only remove generated numeric records, within the dedicated records directory.
    for old in folder.glob('*.json'):
        if old.stem.isdigit():
            old.unlink()
    for record in records:
        (folder / f"{record['number']}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return records, errors


def safe(text):
    return html.escape(str(text)).replace('|', '&#124;').replace('\n', '<br>').replace('[', '&#91;').replace(']', '&#93;').replace('*', '&#42;').replace('`', '&#96;')


def totals(records):
    return len({r['date'] for r in records}), sum(r['minutes'] for r in records)


def build(root, records, repo='Yulu-m/agent-learning-log', today=None, errors=None):
    today = today or datetime.now(TZ).date()
    view = root / 'views'
    view.mkdir(exist_ok=True)
    days = defaultdict(list)
    weeks = defaultdict(list)
    months = defaultdict(list)
    for record in sorted(records, key=lambda r: (r['date'], r['number'])):
        day = date.fromisoformat(record['date'])
        days[day.isoformat()].append(record)
        year, week, _ = day.isocalendar()
        weeks[f'{year}-W{week:02}'].append(record)
        months[day.strftime('%Y-%m')].append(record)
    months.setdefault(today.strftime('%Y-%m'), [])
    def write(path, value):
        target = view / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(value + '\n', encoding='utf-8')
    # Clear only generated daily detail files so date edits don't leave stale entries.
    for old in (view / 'days').glob('*.md') if (view / 'days').exists() else []:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', old.stem):
            old.unlink()
    daily = '# 日视图\n\n[首页](../README.md) · [周视图](weekly.md) · [月视图](monthly.md)\n\n| 日期 | 学习内容 | 时长（分钟） |\n|---|---|---:|\n'
    for day in sorted(days, reverse=True):
        rs = days[day]
        daily += f"| [{day}](days/{day}.md) | {' / '.join(safe(r['topic']) for r in rs)} | {sum(r['minutes'] for r in rs)} |\n"
        detail = f'# {day} 学习记录\n\n[返回日视图](../daily.md)\n'
        for r in rs:
            detail += f"\n## {safe(r['topic'])}\n\n学习时长：{r['minutes']} 分钟 · [编辑原始打卡]({r['url']})\n"
            for label, key in zip(LABELS[3:], ['learned', 'practice', 'questions', 'next', 'moments']):
                detail += f"\n### {label}\n\n{safe(r.get(key, '')) or '未填写'}\n"
        write(f'days/{day}.md', detail)
    if not days:
        daily += '\n还没有打卡。点击首页的「开始打卡」记录第一天。\n'
    write('daily.md', daily)
    weekly = '# 周视图\n\n[首页](../README.md) · [日视图](daily.md) · [月视图](monthly.md)\n\n按周一至周日汇总，跨年周采用 ISO 周编号。\n'
    for week in sorted(weeks, reverse=True):
        rs = weeks[week]
        year, w = map(int, week.split('-W'))
        start = date.fromisocalendar(year, w, 1)
        count, minutes = totals(rs)
        weekly += f'\n## {week}（{start} — {start + timedelta(days=6)}）\n\n学习 {count} 天 · {minutes} 分钟\n\n'
        for day in sorted({r['date'] for r in rs}):
            weekly += f"- [{day}](days/{day}.md)：{' / '.join(safe(r['topic']) for r in rs if r['date'] == day)}\n"
    if not weeks:
        weekly += '\n还没有打卡。\n'
    weekly += '\n[填写周复盘模板](../templates/周复盘.md)\n'
    write('weekly.md', weekly)
    monthly = '# 月视图\n\n[首页](../README.md) · [日视图](daily.md) · [周视图](weekly.md)\n\n日期链接表示当天已打卡，括号内为学习分钟数。\n'
    for month in sorted(months, reverse=True):
        rs = months[month]
        count, minutes = totals(rs)
        monthly += f'\n## {month}\n\n学习 {count} 天 · {minutes} 分钟\n\n| 周一 | 周二 | 周三 | 周四 | 周五 | 周六 | 周日 |\n|---|---|---|---|---|---|---|\n'
        year, m = map(int, month.split('-'))
        for row in calendar.Calendar(firstweekday=0).monthdayscalendar(year, m):
            cells = []
            for n in row:
                key = f'{month}-{n:02}'
                cells.append(f"[**{n}**](days/{key}.md)<br>({sum(r['minutes'] for r in days[key])})" if n and key in days else (str(n) if n else ' '))
            monthly += '| ' + ' | '.join(cells) + ' |\n'
    monthly += '\n[填写月复盘模板](../templates/月复盘.md)\n'
    write('monthly.md', monthly)
    write('errors.md', '# 待修正的打卡\n\n' + ('\n'.join(errors) if errors else '所有打卡格式正常。'))
    count, minutes = totals(records)
    readme = f'''# Agent 学习打卡

每天记录一点，积累自己的 Agent 学习轨迹。

**[✍️ 开始打卡](https://github.com/{repo}/issues/new?template=checkin.yml)** · **[📖 日视图](views/daily.md)** · **[📅 周视图](views/weekly.md)** · **[🗓️ 月视图](views/monthly.md)**

累计学习 **{count} 天** · **{len(records)} 次打卡** · **{minutes} 分钟**

## 怎么用

1. 点击「开始打卡」，填学习主题、时长和今天学了什么，提交 Issue。
2. 稍等 GitHub Actions 完成，刷新页面即可查看日、周、月视图。
3. 补打卡时填写日期；修改记录时编辑原 Issue，视图会重新汇总。

日期默认使用提交当天的北京时间。每天可以打卡多次，学习天数按日期去重，时长累加。关闭 Issue 会保留记录；删除 Issue 或移除标题中的 `[打卡]` 前缀会从视图移除。

## 三种视图

- 日视图：逐日查看学习内容、实践产出、问题与下一步。
- 周视图：周一至周日的学习天数、时长和每日记录。
- 月视图：可点击的月历，以及每月学习统计。

复盘时可复制 [周复盘](templates/周复盘.md) 或 [月复盘](templates/月复盘.md) 模板，另存为自己的笔记。

## 如果视图没有更新

查看 [待修正的打卡](views/errors.md) 和 [Actions 运行结果](https://github.com/{repo}/actions)。日期应为 `YYYY-MM-DD`，时长应为 `0—1440` 的整数分钟。首次使用请确认仓库 Actions 已启用。也可以在「更新学习视图」工作流中点击 Run workflow 手动重建。

只统计仓库所有者本人以 `[打卡]` 开头的 Issues，不会加入示例或虚构记录。原始记录保存在 Issues，汇总数据保存在 `records/`。请勿在打卡中填写 API 密钥或密码。
'''
    (root / 'README.md').write_text(readme, encoding='utf-8')
    form = root / '.github/ISSUE_TEMPLATE/checkin.yml'
    if form.exists():
        source = form.read_text(encoding='utf-8')
        date_field = '''  - type: dropdown
    id: date
    attributes:
      label: 学习日期
      description: 选择提交当天或具体日期；日期列表在每次打卡汇总时刷新。更早日期可在提交后编辑 Issue 的学习日期。
      default: 0
      options:
        - 提交当天（北京时间）
'''
        date_field += ''.join(f'        - "{today - timedelta(days=n)}"\n' for n in range(31))
        source = re.sub(r'  - type: (?:input|dropdown)\n    id: date\n.*?(?=  - type: input\n    id: topic)', lambda _: date_field, source, flags=re.S)
        form.write_text(source, encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sync', action='store_true')
    args = parser.parse_args()
    repo = os.environ.get('GITHUB_REPOSITORY', 'Yulu-m/agent-learning-log')
    if args.sync:
        records, errors = sync(ROOT, repo)
    else:
        records = [json.loads(p.read_text(encoding='utf-8')) for p in (ROOT / 'records').glob('*.json')]
        errors = []
    build(ROOT, records, repo, errors=errors)
