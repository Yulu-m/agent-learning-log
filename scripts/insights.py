"""Deterministic summaries and repo-native charts, with source links."""
import calendar
import html
from collections import defaultdict
from datetime import date, timedelta


def clean(value):
    return html.escape(str(value)).replace('|', '&#124;').replace('\n', '<br>').replace('[', '&#91;').replace(']', '&#93;')


def formal(records):
    return sorted((r for r in records if not r.get('test', False)), key=lambda r: (r['date'], r['number']))


def bullets(records, field, limit=None):
    items = [f"- {clean(r[field])}（[记录 #{r['number']}]({r['url']})）" for r in records if r.get(field)]
    return '\n'.join(items[:limit]) if items else '本期未记录。'


def summarize(records, kind, start, end):
    rs = [r for r in formal(records) if start.isoformat() <= r['date'] <= end.isoformat()]
    days = len({r['date'] for r in rs})
    minutes = sum(r['minutes'] for r in rs)
    parts = [f'# Agent 学习{"日报" if kind == "daily" else "周报" if kind == "weekly" else "月报"}',
             f'统计周期：{start} — {end}（北京时间）', f'学习 {days} 天 · {len(rs)} 次正式记录 · {minutes} 分钟']
    if not rs:
        parts.append('本期没有正式学习打卡；测试记录不计入。')
    if kind == 'daily':
        for r in rs:
            parts.append(f"## {clean(r['topic'])}\n\n[原始打卡]({r['url']}) · {r['minutes']} 分钟")
            for label, field in [('学了什么', 'learned'), ('做出了什么', 'practice'), ('问题与收获', 'questions'), ('掌握程度（自评）', 'mastery'), ('今日拾光', 'moments')]:
                if r.get(field):
                    parts.append(f'### {label}\n\n{clean(r[field])}')
        parts.append('## 今天从这里开始\n\n' + bullets(rs, 'next', 3))
    else:
        groups = defaultdict(list)
        for r in rs:
            groups[r.get('category', '其他')].append(r)
        parts.append('## 学习主线\n\n' + ('\n'.join(f"- {clean(k)}：{len(v)} 次记录，{sum(r['minutes'] for r in v)} 分钟" for k, v in sorted(groups.items())) or '本期未记录。'))
        parts.append('## 掌握了什么（依据打卡）\n\n' + bullets(rs, 'learned'))
        parts.append('## 可展示的成果\n\n' + bullets(rs, 'practice'))
        parts.append('## 能力变化（个人自评）\n\n' + mastery_changes(rs))
        parts.append('## 待复查的问题与收获\n\n' + bullets(rs, 'questions'))
        parts.append('## 下一阶段行动（最多三项）\n\n' + bullets(rs, 'next', 3))
        parts.append('## 复盘建议\n\n' + ('把一项学习内容做成可运行的小项目，并检查上面的待复查问题是否已经解决。此段是建议，不代表已完成。' if rs else '下一阶段先完成一次短打卡，记录一个具体收获。此段是建议。'))
        parts.append('## 本期拾光\n\n' + bullets(rs, 'moments', 5))
    return '\n\n'.join(parts) + '\n'


def mastery_changes(records):
    groups = defaultdict(list)
    for r in records:
        if r.get('mastery') and r['mastery'] != '未评估':
            groups[r.get('category', '其他')].append(r)
    return '\n'.join(f"- {clean(category)}：{clean(rs[0]['mastery'])} → {clean(rs[-1]['mastery'])}（自评，非客观测验）" for category, rs in sorted(groups.items())) or '本期没有掌握程度自评，无法推断能力变化。'


def bars(items, title, unit):
    width, height = 760, max(150, 70 + len(items) * 42)
    max_value = max((v for _, v in items), default=1) or 1
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}"><rect width="100%" height="100%" rx="14" fill="#f6f8fa"/><g font-family="Arial, sans-serif" font-size="14" fill="#24292f">', f'<text x="24" y="30" font-size="18">{html.escape(title)}</text>']
    if not items:
        svg.append('<text x="24" y="85">暂无正式记录</text>')
    for i, (label, value) in enumerate(items):
        y = 60 + i * 42
        svg.append(f'<text x="24" y="{y+18}">{html.escape(label[:18])}</text><rect x="210" y="{y}" width="{value/max_value*420:.1f}" height="25" rx="4" fill="#2da44e"/><text x="650" y="{y+18}">{value:g} {html.escape(unit)}</text>')
    return ''.join(svg) + '</g></svg>\n'


def heatmap(records, today):
    first = today.replace(day=1)
    values = defaultdict(int)
    seen = set()
    for r in records:
        values[r['date']] += r['minutes']
        seen.add(r['date'])
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="500" height="320" viewBox="0 0 500 320" role="img" aria-label="月度学习热力图"><rect width="100%" height="100%" rx="14" fill="#f6f8fa"/><g font-family="Arial, sans-serif" font-size="14" fill="#24292f">', f'<text x="22" y="30" font-size="18">{today:%Y-%m} 学习热力图</text>']
    for i, name in enumerate(['一', '二', '三', '四', '五', '六', '日']):
        svg.append(f'<text x="{28+i*64}" y="60">{name}</text>')
    for row, week in enumerate(calendar.Calendar(0).monthdayscalendar(today.year, today.month)):
        for col, day in enumerate(week):
            if not day:
                continue
            key = first.replace(day=day).isoformat()
            val = values[key]
            shade = '#ebedf0' if key not in seen else '#9be9a8' if val < 30 else '#40c463' if val < 90 else '#216e39'
            x, y = 22 + col*64, 72 + row*35
            svg.append(f'<rect x="{x}" y="{y}" width="52" height="29" rx="5" fill="{shade}"><title>{key}：{val} 分钟</title></rect><text x="{x+15}" y="{y+20}" fill="{"#fff" if val >= 90 else "#24292f"}">{day}</text>')
    svg.append('<text x="22" y="295">灰：未打卡 · 浅绿：0–29 · 绿：30–89 · 深绿：90+ 分钟</text>')
    return ''.join(svg) + '</g></svg>\n'


def build_insights(root, records, repo, today):
    rs = formal(records)
    view = root / 'views'
    assets = view / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    def write(name, text):
        (view / name).write_text(text + '\n', encoding='utf-8')
    categories, months = defaultdict(int), defaultdict(int)
    for r in rs:
        categories[r.get('category', '其他')] += r['minutes']
        months[r['date'][:7]] += r['minutes']
    (assets / 'heatmap.svg').write_text(heatmap(rs, today), encoding='utf-8')
    (assets / 'topics.svg').write_text(bars(sorted(categories.items(), key=lambda x: -x[1]), '学习方向分布', '分钟'), encoding='utf-8')
    (assets / 'trend.svg').write_text(bars([(m, v/60) for m, v in sorted(months.items())[-6:]], '最近六个有记录月份的累计时长', '小时'), encoding='utf-8')
    achievements = [r for r in rs if r.get('practice')]
    write('dashboard.md', '# 学习看板\n\n[首页](../README.md) · [成果清单](achievements.md) · [今日拾光](moments.md)\n\n' + f'正式记录 {len(rs)} 次 · 学习 {len({r["date"] for r in rs})} 天 · {sum(r["minutes"] for r in rs)} 分钟 · 有产出的记录 {len(achievements)} 次\n\n' + '![月度热力图](assets/heatmap.svg)\n\n![方向分布](assets/topics.svg)\n\n![累计时长](assets/trend.svg)\n\n掌握程度来自个人自评；热力图不包含测试记录。比连续天数更值得关注的是完成的成果。')
    write('achievements.md', '# 成果清单\n\n[首页](../README.md)\n\n' + bullets(achievements, 'practice'))
    moments = '# 今日拾光\n\n[首页](../README.md) · [学习看板](dashboard.md)\n'
    for r in reversed(rs):
        if r.get('moments'):
            moments += f"\n## {r['date']}\n\n{clean(r['moments'])}\n\n[原始记录]({r['url']})\n"
    write('moments.md', moments if any(r.get('moments') for r in rs) else moments + '\n还没有生活记录。')
    tests = [r for r in records if r.get('test', False)]
    write('testing.md', '# 测试记录\n\n[首页](../README.md)\n\n以下记录仅用于验收，不计入学习统计、正式邮件和生活视图。\n\n' + ('\n'.join(f"- [{clean(r['topic'])}]({r['url']}) · {r['date']}" for r in tests) or '暂无测试记录。'))
    summary = view / 'summaries'
    summary.mkdir(exist_ok=True)
    links = []
    for key in sorted({r['date'][:7] for r in rs}, reverse=True):
        year, month = map(int, key.split('-'))
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        (summary / f'month-{key}.md').write_text(summarize(rs, 'monthly', start, end), encoding='utf-8')
        links.append(f'- [月复盘 {key}](summaries/month-{key}.md)')
    week_starts = {date.fromisoformat(r['date']) - timedelta(days=date.fromisoformat(r['date']).weekday()) for r in rs}
    for start in sorted(week_starts, reverse=True):
        year, w, _ = start.isocalendar()
        key = f'{year}-W{w:02}'
        (summary / f'week-{key}.md').write_text(summarize(rs, 'weekly', start, start+timedelta(days=6)), encoding='utf-8')
        links.append(f'- [周复盘 {key}](summaries/week-{key}.md)')
    # Remove generated summaries that no longer have any formal records after edits.
    expected = {line.split('(summaries/')[1].split(')')[0] for line in links}
    for path in summary.glob('*.md'):
        if path.name.startswith(('week-', 'month-')) and path.name not in expected:
            path.unlink()
    write('summaries.md', '# 周月复盘\n\n[首页](../README.md)\n\n当期复盘反映目前已提交的记录；正式周月邮件仅统计完整的上一周期。\n\n' + ('\n'.join(links) or '暂无正式记录。'))
