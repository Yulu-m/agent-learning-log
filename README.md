# Agent 学习打卡

每天记录一点，积累自己的 Agent 学习轨迹。

**[✍️ 开始打卡](https://agent-journal-yulu.wavyjam9.chatgpt.site)** · **[📖 日视图](views/daily.md)** · **[📅 周视图](views/weekly.md)** · **[🗓️ 月视图](views/monthly.md)**

[学习看板](views/dashboard.md) · [成果清单](views/achievements.md) · [周月复盘](views/summaries.md) · [今日拾光](views/moments.md)

累计学习 **1 天** · **1 次打卡** · **0 分钟**

## 最近学习与笔记

### 2026-10-11 · 规划、任务分解、多智能体协作

[完整记录](views/days/2026-10-11.md) · [编辑打卡](https://github.com/Yulu-m/agent-learning-log/issues/2)

**学习内容**

1.agent对未来会做的事情的一种明确自然语言表示,随机应变<br>2.反馈，对环境的反馈，进行反思，重规划


## 怎么用

1. 点击「开始打卡」进入专门页面，随时补充并保存草稿；完成后提交，在 GitHub 确认创建 Issue，再回页面检查结果。只有学习内容必填，其余选填。
2. 稍等 GitHub Actions 完成，刷新页面即可查看日、周、月视图。
3. 补打卡时填写日期；修改记录时编辑原 Issue，视图会重新汇总。

专门页面的草稿仅保存在当前浏览器，支持导出、导入备份，未提交的草稿不进入统计或邮件。

日期默认使用提交当天的北京时间。每天可以打卡多次，学习天数按日期去重，时长累加。关闭 Issue 会保留记录；删除 Issue 或移除标题中的 `[打卡]` 前缀会从视图移除。

填写「学习方向」便于查看主题分布；「掌握程度」为个人自评。选择「测试记录」不会计入学习统计、生活视图或正式邮件。历史的「测试打卡」也会自动隔离。

## 三种视图

- 日视图：逐日查看学习内容、实践产出、问题与下一步。
- 周视图：周一至周日的学习天数、时长和每日记录。
- 月视图：可点击的月历，以及每月学习统计。

复盘时可复制 [周复盘](templates/周复盘.md) 或 [月复盘](templates/月复盘.md) 模板，另存为自己的笔记。

## 如果视图没有更新

查看 [待修正的打卡](views/errors.md) 和 [Actions 运行结果](https://github.com/Yulu-m/agent-learning-log/actions)。日期应为 `YYYY-MM-DD`，时长应为 `0—1440` 的整数分钟。首次使用请确认仓库 Actions 已启用。也可以在「更新学习视图」工作流中点击 Run workflow 手动重建。

只统计仓库所有者本人以 `[打卡]` 开头的正式 Issues。原始记录保存在 Issues，汇总数据保存在 `records/`。仓库公开时，记录也公开；请勿填写 API 密钥或密码。

## 邮件与复盘

北京时间每日 10:00 发送昨天记录，并提醒今天的下一步；周一 10:00 发送完整上周复盘；每月 1 日 10:00 发送完整上月复盘。周月总结结合成果、自评变化、待复查问题和下一阶段最多三项行动，建议与已完成事实分开。

邮件在 GitHub Actions 运行，配置说明见 [邮件设置](docs/email-setup.md)。未配置发件凭据时只生成预览，不发送。GitHub 调度可能延迟，不能保证整点送达。发送日志不包含密码或邮箱地址，支持手动重试及报告去重。
<details>
<summary>设置与维护</summary>

**邮件设置**：[发送开关](https://github.com/Yulu-m/agent-learning-log/actions/workflows/mail-settings.yml) · [配置说明](docs/email-setup.md)

**维护工具**：[测试记录](views/testing.md) · [待修正的打卡](views/errors.md) · [运行日志](https://github.com/Yulu-m/agent-learning-log/actions)

</details>


