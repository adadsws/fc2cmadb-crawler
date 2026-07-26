# README 介绍视频链接实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 README 顶部简介中加入指定的 Bilibili 介绍视频链接，并通过脱敏导出仓库发布到远程 `main`。

**Architecture:** 仅修改 README 一行，不改变其他用户文档或程序。完成本地验证和 commit 后归档全部 `docs/superpowers/` 已完成文档，再将 README 复制到现有 `output/github-export/` 导出仓库，创建单一 fast-forward 发布 commit。

**Tech Stack:** Markdown、PowerShell、Git、GitHub CLI

## Global Constraints

- 链接文本固定为“介绍视频（哔哩哔哩）”。
- 链接固定为 `https://www.bilibili.com/video/BV11zzfBMEWu`。
- 链接位于项目用途说明与免责声明之间。
- 不新增章节、缩略图、徽章或额外说明。
- `docs/superpowers/` 完成后必须为空；已完成规格和计划移入 `~archived/superpowers-plans/`。
- `~archived/` 和 `docs/superpowers/` 不得 push。
- 远程发布只通过 `output/github-export/`，仅允许 fast-forward push `main`。

---

### Task 1: 添加视频链接并完成本地提交

**Files:**
- Modify: `README.md`
- Move: `docs/superpowers/specs/2026-07-26-agents-compliance-design.md` → `~archived/superpowers-plans/2026-07-26-agents-compliance-design.md`
- Move: `docs/superpowers/specs/2026-07-26-readme-user-facing-design.md` → `~archived/superpowers-plans/2026-07-26-readme-user-facing-design.md`
- Move: `docs/superpowers/specs/2026-07-26-readme-intro-video-design.md` → `~archived/superpowers-plans/2026-07-26-readme-intro-video-design.md`
- Move: `docs/superpowers/plans/2026-07-26-readme-intro-video.md` → `~archived/superpowers-plans/2026-07-26-readme-intro-video.md`

**Interfaces:**
- Consumes: README 顶部用途说明和免责声明
- Produces: 唯一的视频链接，以及空的 `docs/superpowers/`

- [ ] **Step 1: 运行链接检测并确认失败**

```powershell
$readme = Get-Content -LiteralPath 'README.md' -Raw -Encoding UTF8
if (([regex]::Matches($readme, 'BV11zzfBMEWu')).Count -ne 1) {
    throw 'README 尚未且仅包含一次指定视频'
}
```

Expected: 失败，因为 README 中尚未出现 BV 号。

- [ ] **Step 2: 添加精确 Markdown**

在用途说明后、免责声明前插入：

```markdown
[介绍视频（哔哩哔哩）](https://www.bilibili.com/video/BV11zzfBMEWu)
```

- [ ] **Step 3: 验证链接内容与位置**

```powershell
$lines = Get-Content -LiteralPath 'README.md' -Encoding UTF8
$link = '[介绍视频（哔哩哔哩）](https://www.bilibili.com/video/BV11zzfBMEWu)'
$linkIndex = [Array]::IndexOf($lines, $link)
$purposeIndex = [Array]::IndexOf($lines, '用于抓取 `fc2cmadb.com` 演员影片信息，并按作品自动创建文件夹和 `.url` 快捷方式。')
$noticeIndex = [Array]::IndexOf($lines, '请不要滥用本脚本。如本项目侵犯版权，请联系删除。')
if (($lines -match 'BV11zzfBMEWu').Count -ne 1) { throw '视频链接不是唯一值' }
if ($linkIndex -le $purposeIndex -or $linkIndex -ge $noticeIndex) { throw '视频链接位置不正确' }
```

Expected: BV 号出现一次，链接位于用途说明和免责声明之间。

- [ ] **Step 4: 归档全部已完成 Superpowers 文档**

将 Task 1 “Files”列出的三个规格和本计划移动到
`~archived/superpowers-plans/`。不得删除文件。

- [ ] **Step 5: 验证并创建本地 commit**

```powershell
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' diff --check -- README.md
$active = @(Get-ChildItem -LiteralPath 'docs/superpowers' -File -Recurse -ErrorAction SilentlyContinue)
if ($active.Count -ne 0) { throw 'docs/superpowers 仍包含已完成文档' }
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -v
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' add -- README.md docs/superpowers ~archived/superpowers-plans
git -c safe.directory='D:/CODE/PY/crawler_for_fc_newsite' commit -m "docs: add introduction video"
```

Expected: 3 个测试通过；提交作者邮箱为 `1410990013@qq.com`。

---

### Task 2: 脱敏导出并 push

**Files:**
- Modify: `output/github-export/README.md`

**Interfaces:**
- Consumes: Task 1 已提交的 `README.md`
- Produces: 远程 `main` 上仅含 README 视频链接的一次 fast-forward commit

- [ ] **Step 1: 同步并检查导出仓库**

```powershell
git -C output/github-export fetch origin main
git -C output/github-export merge-base --is-ancestor HEAD origin/main
git -C output/github-export status --short --branch
```

Expected: 导出仓库干净，HEAD 等于 `origin/main`，本地和远程只有 `main`。

- [ ] **Step 2: 复制并验证唯一差异**

```powershell
Copy-Item -LiteralPath 'README.md' -Destination 'output/github-export/README.md' -Force
$changed = @(git -C output/github-export diff --name-only)
if (($changed -join "`n") -ne 'README.md') { throw '导出差异不止 README' }
git -C output/github-export diff --check -- README.md
```

Expected: 唯一差异为 README 中新增的一行视频链接。

- [ ] **Step 3: 测试并创建导出 commit**

```powershell
git -C output/github-export add -- README.md
$env:PYTHONDONTWRITEBYTECODE='1'
Push-Location 'output/github-export'
python -m unittest discover -s tests -v
Pop-Location
git -C output/github-export commit -m "Add introduction video"
```

Expected: 3 个测试通过；commit 作者与 committer 均为
`adadsws <1410990013@qq.com>`。

- [ ] **Step 4: 运行 push 门禁并 fast-forward push**

```powershell
git -C output/github-export fetch origin main
git -C output/github-export merge-base --is-ancestor origin/main HEAD
git -C output/github-export push origin main:main
```

Expected: 只将一个 README commit fast-forward push 到远程 `main`；
不创建分支、PR，不 force push。

- [ ] **Step 5: 最终核验**

使用 GitHub API 确认：

- 远程只有 `main`；
- 远程 `main` SHA 等于导出仓库 HEAD；
- GitHub author 和 committer 都是 `adadsws`；
- 提交邮箱是 `1410990013@qq.com`；
- 源仓库、导出仓库工作树无非忽略改动。
