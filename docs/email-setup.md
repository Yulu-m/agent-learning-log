# Gmail 独立发件设置

GitHub Actions 每天按北京时间 10:00 调度日报；周一同时生成完整上周周报，1 日同时生成上月月报。不需要本机开机。GitHub 高峰时可能延迟，公开仓库长期没有活动可能停用定时任务；不能保证邮件整点送达。

## 日报、周报、月报独立开关

打开 [邮件发送开关](https://github.com/Yulu-m/agent-learning-log/actions/workflows/mail-settings.yml) → Run workflow，在 main 分支选择：

- 日报邮件：保持现状 / 开启 / 关闭
- 周报邮件：保持现状 / 开启 / 关闭
- 月报邮件：保持现状 / 开启 / 关闭

点击 Run workflow 保存。运行 Summary 展示保存后的三项状态；长期设置保存在 [mail-settings.json](../config/mail-settings.json)，默认三项均开启。关闭某项会阻止该类定时邮件和手动正式邮件发送，也不会创建发送占用日志；学习打卡、图表和复盘照常生成。已经进入 SMTP 发送中的邮件无法撤回；重新开启不会自动补发以前关闭期间的邮件。

独立测试邮件 test 不受日周月开关影响，只有手动选择 test 且取消 preview 才发送。所有设置均在 GitHub 云端生效，无需打开 Codex。

## 最后一步：配置三个 Secrets

打开仓库 Settings → Secrets and variables → Actions → New repository secret：

| 名称 | 填写内容 |
|---|---|
| SMTP_USERNAME | 用来发信的完整 Gmail 地址 |
| SMTP_PASSWORD | 该 Gmail 的应用专用密码 |
| MAIL_TO | 你的收件邮箱 |

不要提交 `.env`，不要把应用专用密码填进 Issue 或聊天。应用专用密码与日常登录密码不同；在 Google 账号的安全设置中创建。账号需满足 Google 的应用密码使用条件，部分组织或高级保护账号不支持。

官方说明：[Google 应用专用密码](https://support.google.com/accounts/answer/185833)。[GitHub Secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)。

## 验证并完成迁移

1. 在 Actions 打开「学习日报周报月报邮件」→ Run workflow。
2. 先选择 `test`、保持 preview 勾选，检查 `mail-preview` 附件。
3. 再选择 `test`、取消 preview，执行一次真实发件。
4. 确认收件箱和 `delivery/test-日期-日期.json` 为 `sent`。在 Codex 本聊天告知测试成功，停用旧定时任务，避免两套任务重复发送。

缺少 Secrets 时只生成预览，会在运行日志中说明，不能视为邮件发送成功。

## 日志、去重和重试

`delivery/` 保存报告周期、状态和时间，不保存邮箱、密码、正文。相同周期成功发送后不会再发；`failed` 状态可以手动重跑。`pending` 或 `unknown` 表示发送回执不确定或任务中断，为避免重复，不会自动重发。先检查 Gmail 已发送和收件箱；确需重发时通过 GitHub 编辑该周期日志，将状态改为 `failed`，再运行对应报告。不要在未核对时改状态。

SMTP 登录/连接的安全失败以及服务器明确拒收的临时错误会有限重试；发送后连接断开时不自动重试，因为邮件可能已经被服务器接受。SMTP 不提供端到端的严格仅发送一次或收件箱送达保证。

## 手动预览

`python scripts/mail.py --preview --kind weekly --date 2026-10-12`

指定日期只允许预览；默认真实发送使用北京时间当前日期。测试打卡始终排除在正式报告外。
