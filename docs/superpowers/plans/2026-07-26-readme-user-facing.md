# README 用户文档收敛实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从 README 移除 `AGENTS.md` 的内部协作规则，同时完整保留最终用户安装和运行项目所需的信息。

**Architecture:** 仅编辑 README 的 Cookie 后续段落和目录树，不改变代码、配置或其他用户文档。通过禁止词与必需词检查验证边界，完成后将本计划归档并创建本地提交。

**Tech Stack:** Markdown、PowerShell、Git

## Global Constraints

- README 只面向安装和使用项目的最终用户。
- 保留 Cookie 配置路径、`.example`、运行命令、工具和输出目录说明。
- 移除内部 Git 跟踪、归档、脱敏导出和发布流程。
- 不修改程序、测试、配置或远程仓库。
- 完成的实施计划必须移入 `~archived/superpowers-plans/`，不得删除。
- 修改后必须创建本地 Git commit，不自动 push。

---

### Task 1: 收敛 README 并归档计划

**Files:**
- Modify: `README.md`
- Move: `docs/superpowers/plans/2026-07-26-readme-user-facing.md` → `~archived/superpowers-plans/2026-07-26-readme-user-facing.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-26-readme-user-facing-design.md`
- Produces: 仅含最终用户说明的 `README.md`

- [ ] **Step 1: 运行旧内容检测并确认失败**

Run:

```powershell
$readme = Get-Content -LiteralPath 'README.md' -Raw -Encoding UTF8
$forbidden = @(
    '## 脱敏发布',
    'output/github-export/',
    '~ref/',
    '~archived/',
    '~temp/',
    'pre-push',
    'fast-forward',
    'force push',
    '真实 Cookie 会进入本地 Git'
)
foreach ($text in $forbidden) {
    if ($readme.Contains($text)) { throw "README 包含内部规则：$text" }
}
```

Expected: 检查失败，首个原因是 `README 包含内部规则：## 脱敏发布`。

- [ ] **Step 2: 删除内部协作内容**

在 `README.md` 中：

1. 删除 Cookie 章节末尾以“真实 Cookie 会进入本地 Git”开头的段落；
2. 删除完整的“脱敏发布”章节；
3. 把目录树末尾改为：

```text
├── CHANGELOG.md
├── secrets/                   # Cookie 配置与脱敏示例
├── recommend_20260629/
└── output/                    # 生成输出
```

- [ ] **Step 3: 运行禁止词与必需词检查**

Run:

```powershell
$readme = Get-Content -LiteralPath 'README.md' -Raw -Encoding UTF8
$forbidden = @(
    '## 脱敏发布',
    'output/github-export/',
    '~ref/',
    '~archived/',
    '~temp/',
    'pre-push',
    'fast-forward',
    'force push',
    '真实 Cookie 会进入本地 Git'
)
$required = @(
    'secrets/fc2cmadb.com_cookies.txt',
    'secrets/fc2cmadb.com_cookies.txt.example',
    'python main.py',
    'output/'
)
foreach ($text in $forbidden) {
    if ($readme.Contains($text)) { throw "README 包含内部规则：$text" }
}
foreach ($text in $required) {
    if (-not $readme.Contains($text)) { throw "README 缺少用户说明：$text" }
}
```

Expected: 无异常，命令退出码为 0。

- [ ] **Step 4: 检查差异范围**

Run:

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' diff --check -- README.md
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' diff --stat
```

Expected: README 无空白错误；除本计划归档外，内容差异只涉及 `README.md`。

- [ ] **Step 5: 归档实施计划**

将：

```text
docs/superpowers/plans/2026-07-26-readme-user-facing.md
```

移动到：

```text
~archived/superpowers-plans/2026-07-26-readme-user-facing.md
```

- [ ] **Step 6: 暂存并最终验证**

Run:

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' add -- README.md docs/superpowers/plans/2026-07-26-readme-user-facing.md ~archived/superpowers-plans/2026-07-26-readme-user-facing.md
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' diff --cached --check -- README.md
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' status --short
```

Expected: 暂存区只有 README 修改和实施计划移动。

- [ ] **Step 7: 创建本地提交**

Run:

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' commit -m "docs: keep README user-facing"
```

Expected: 提交成功，作者邮箱为 `1410990013@qq.com`；不得运行 `git push`。
