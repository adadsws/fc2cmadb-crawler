# 全局 AGENTS.md 合规收尾实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 可恢复地归档旧导出分支，并让当前仓库的分支、发布说明、计划归档和本地 Git 状态严格满足更新后的全局 `AGENTS.md`。

**Architecture:** 先将旧导出分支封装为可验证的 Git bundle，确认归档完整后再移除该分支。随后统一 README 和 CHANGELOG 中的发布边界，最终把已完成计划移入 `~archived/`，运行代码、隐私、跟踪状态和分支检查后创建本地提交。

**Tech Stack:** PowerShell、Git、Python 3 标准库、`unittest`

## Global Constraints

- `output/` 只存输出，`~temp/` 只存临时文件；两者必须写入 `.gitignore`，不纳入 Git。
- 除 `output/` 和 `~temp/` 外，所有内容必须纳入本地 Git 并 commit。
- `~archived/`、`~ref/` 和真实 `secrets/**` 只允许本地 Git 记录，禁止 push。
- 任何分支移除前必须先创建并验证可恢复归档；不得丢失旧分支内容。
- 源仓库最终只保留 `main`；本次不得执行 `git push`。
- 远程发布只允许通过 `output/github-export/` 中的脱敏导出仓库完成。
- 完成的实施计划必须移入 `~archived/superpowers-plans/`，不得删除。
- 文档、注释优先使用简体中文。
- 当前项目不是 WebUI；不得为 `api_version` 新增无关配置。

---

### Task 1: 可恢复地归档旧导出分支

**Files:**
- Create: `~archived/git-branches/sanitized-export-20260726.bundle`

**Interfaces:**
- Consumes: 本地分支 `codex/sanitized-export-20260726`
- Produces: 可由 `git clone <bundle>` 或 `git fetch <bundle>` 恢复的完整分支归档

- [ ] **Step 1: 记录并验证原分支引用**

Run:

```powershell
$branchName = 'codex/sanitized-export-20260726'
$expectedTip = git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' rev-parse $branchName
if ($LASTEXITCODE -ne 0 -or -not $expectedTip) { throw "找不到旧导出分支：$branchName" }
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' show-ref --verify "refs/heads/$branchName"
```

Expected: `show-ref` 输出的提交为
`a2934f4a0a5d66b426f87c92dd8ddc57f98e460c`，且 `$expectedTip` 与它一致。

- [ ] **Step 2: 确认归档目标不会被覆盖**

Run:

```powershell
$bundlePath = '~archived/git-branches/sanitized-export-20260726.bundle'
if (Test-Path -LiteralPath $bundlePath) { throw "归档已存在，停止以避免覆盖：$bundlePath" }
New-Item -ItemType Directory -Path '~archived/git-branches' -Force
```

Expected: 目标原先不存在，目录创建或已存在；没有文件被覆盖。

- [ ] **Step 3: 创建只包含旧分支的 bundle**

Run:

```powershell
$branchName = 'codex/sanitized-export-20260726'
$bundlePath = '~archived/git-branches/sanitized-export-20260726.bundle'
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' bundle create $bundlePath $branchName
if ($LASTEXITCODE -ne 0) { throw 'git bundle create 失败' }
```

Expected: 命令退出码为 0，bundle 文件存在且长度大于 0。

- [ ] **Step 4: 验证 bundle 完整性和 tip**

Run:

```powershell
$branchName = 'codex/sanitized-export-20260726'
$bundlePath = '~archived/git-branches/sanitized-export-20260726.bundle'
$expectedTip = git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' rev-parse $branchName
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' bundle verify $bundlePath
$bundleHeads = git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' bundle list-heads $bundlePath
if ($bundleHeads -notmatch [regex]::Escape($expectedTip)) { throw 'bundle 不包含原分支 tip' }
```

Expected: `git bundle verify` 成功，并且 `list-heads` 同时包含 `$expectedTip`
和 `refs/heads/codex/sanitized-export-20260726`。

- [ ] **Step 5: 验证归档后移除旧分支**

Run:

```powershell
$branchName = 'codex/sanitized-export-20260726'
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' branch -D $branchName
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' for-each-ref --format='%(refname:short)' refs/heads/
```

Expected: 分支删除成功，本地分支输出只有 `main`。若 bundle 验证失败，不执行本步骤。

---

### Task 2: 统一新版发布说明

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: 全局 `AGENTS.md` 的脱敏导出流程
- Produces: 唯一且可执行的 `output/github-export/` 发布说明，以及本次合规收尾记录

- [ ] **Step 1: 先写文档合规检查并确认失败**

Run:

```powershell
$readme = Get-Content -LiteralPath 'README.md' -Raw -Encoding UTF8
if ($readme -match '(?i)orphan') { throw 'README 仍包含旧 orphan 发布方式' }
foreach ($required in @(
    'output/github-export/',
    'fast-forward',
    'pre-push',
    '~archived/',
    '~ref/',
    'secrets/'
)) {
    if ($readme -notmatch [regex]::Escape($required)) {
        throw "README 缺少新版发布要求：$required"
    }
}
```

Expected: 检查失败，原因至少包括 README 仍包含 `orphan`。

- [ ] **Step 2: 更新 README 的隐私与发布章节**

在 Cookie 章节移除“无历史 orphan 分支”建议，并新增“脱敏发布”章节，明确：

```text
1. 不得从源仓库直接 push。
2. 将远程 main 克隆到 output/github-export/。
3. 只复制允许发布的源码、测试、必要文档和脱敏示例。
4. 不复制 ~archived/、~ref/、真实 secrets/** 和原始隐私 data/。
5. 大目录若不适合 push，用同名 .md 记录用途、来源、版本和重建方式。
6. 检查待发布文件、导出仓库历史和隐私，运行测试及 pre-push hook。
7. 导出仓库只保留 main；远程有更新时先同步，只允许 fast-forward push。
8. push 后确认源仓库、导出仓库和远程都只有 main。
9. 源仓库继续保留本地私有历史，不合并远程脱敏历史。
```

- [ ] **Step 3: 更新 CHANGELOG**

在 `2026-07-26` 的“仓库维护”下新增：

```markdown
- **严格发布隔离**：发布流程统一为 `output/github-export/` 脱敏导出仓库，不再使用源仓库分支或 orphan 历史直接发布。
- **归档旧导出分支**：旧的 `codex/sanitized-export-20260726` 已保存为经验证的 Git bundle，源仓库仅保留 `main`。
- **归档已完成计划**：已完成的实施计划移入 `~archived/superpowers-plans/`，不再留在活动计划目录。
```

- [ ] **Step 4: 运行文档合规检查并确认通过**

重新运行 Step 1 的 PowerShell 检查。

Expected: 无异常，命令退出码为 0。

---

### Task 3: 归档计划并完成仓库验证

**Files:**
- Move: `docs/superpowers/plans/2026-07-26-agents-compliance.md` → `~archived/superpowers-plans/2026-07-26-agents-compliance.md`
- Move: `docs/superpowers/plans/2026-07-26-agents-compliance-finalization.md` → `~archived/superpowers-plans/2026-07-26-agents-compliance-finalization.md`
- Add: `~archived/git-branches/sanitized-export-20260726.bundle`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 的有效 bundle 与 Task 2 的发布说明
- Produces: 无活动已完成计划、仅有 `main`、除输出/临时目录外全部跟踪的本地仓库

- [ ] **Step 1: 归档两个已完成计划**

Run:

```powershell
$planArchive = '~archived/superpowers-plans'
New-Item -ItemType Directory -Path $planArchive -Force
Move-Item -LiteralPath 'docs/superpowers/plans/2026-07-26-agents-compliance.md' -Destination $planArchive
Move-Item -LiteralPath 'docs/superpowers/plans/2026-07-26-agents-compliance-finalization.md' -Destination $planArchive
```

Expected: 两个计划均位于归档目录；`docs/superpowers/plans/` 中不再有已完成计划。

- [ ] **Step 2: 运行代码验证**

Run:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py fc2cmadb_crawler tests
```

Expected: 3 个测试全部通过，编译检查退出码为 0。

- [ ] **Step 3: 验证忽略规则与本地跟踪边界**

Run:

```powershell
$ignoreLines = Get-Content -LiteralPath '.gitignore' -Encoding UTF8 |
    Where-Object { $_.Trim() -and -not $_.Trim().StartsWith('#') }
if (@($ignoreLines) -join "`n" -ne "output/`n~temp/") {
    throw '.gitignore 必须只包含 output/ 和 ~temp/'
}
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' status --short --ignored
```

Expected: ignored 项只有 `output/` 和存在时的 `~temp/`；其他改动均显示为已跟踪修改或未跟踪待加入内容。

- [ ] **Step 4: 验证隐私文件配对且示例未泄露真实值**

Run:

```powershell
$secretPath = 'secrets/fc2cmadb.com_cookies.txt'
$examplePath = 'secrets/fc2cmadb.com_cookies.txt.example'
if (-not (Test-Path -LiteralPath $secretPath) -or
    -not (Test-Path -LiteralPath $examplePath)) {
    throw '真实 Cookie 或对应 .example 缺失'
}
$realValues = Get-Content -LiteralPath $secretPath -Encoding UTF8 |
    Where-Object { $_ -and -not $_.StartsWith('#') } |
    ForEach-Object { ($_ -split "`t")[-1] } |
    Where-Object { $_ }
$example = Get-Content -LiteralPath $examplePath -Raw -Encoding UTF8
foreach ($value in $realValues) {
    if ($example.Contains($value)) { throw 'Cookie 示例包含真实值' }
}
```

Expected: 无异常；命令不得输出任何真实 Cookie 值。

- [ ] **Step 5: 暂存并检查完整改动**

Run:

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' add -A
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' diff --cached --check -- . ':(exclude)~archived/**'
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' status --short --ignored
```

Expected:

- `output/` 与 `~temp/` 未进入暂存区；
- bundle、两个归档计划、README 和 CHANGELOG 已暂存；
- `docs/superpowers/plans/` 不再包含已完成计划；
- 活动文件的 `diff --check` 无输出。

- [ ] **Step 6: 创建本地提交**

Run:

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' commit -m "chore: finalize AGENTS compliance"
```

Expected: 提交成功；不得运行 `git push`。

- [ ] **Step 7: 提交后最终复核**

Run:

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' status --short --branch --ignored
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' for-each-ref --format='%(refname:short)' refs/heads/
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' for-each-ref --format='%(refname:short)' refs/remotes/
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' bundle verify '~archived/git-branches/sanitized-export-20260726.bundle'
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' log -5 --oneline --decorate
```

Expected:

- 工作树除 `output/`、`~temp/` 的 ignored 提示外保持干净；
- 本地分支只有 `main`，远程跟踪分支只有 `origin/main`；
- bundle 验证成功；
- 最新提交为 `chore: finalize AGENTS compliance`；
- 未执行任何远程 push。
