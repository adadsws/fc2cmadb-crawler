# 全局 AGENTS.md 合规整改实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让当前仓库严格满足全局 `AGENTS.md` 的文件布局、隐私示例、Git 跟踪、文档和提交要求。

**Architecture:** 在配置层新增统一的 `secrets/` 路径，Cookie 查找函数按“新位置优先、旧位置兼容”的顺序解析文件。仓库层将忽略范围收敛为 `output/` 和 `~temp/`，以 Git 引用记录 `~ref/grill-with-docs`，并把其余现有内容纳入本地历史。

**Tech Stack:** Python 3 标准库、`unittest`、PowerShell、Git

## Global Constraints

- `output/` 只存输出，`~temp/` 只存临时文件；两者必须写入 `.gitignore`，不提交。
- 除 `output/` 和 `~temp/` 外，本地 Git 必须跟踪并提交所有内容。
- 真实隐私文件必须保留，并提供不含真实值且保留结构与说明的 `.example`。
- 不删除任何文件；旧文件只允许移动或归档。
- 含真实隐私值或其历史的当前仓库和分支不得直接推送。
- 文档、注释优先使用简体中文。
- 本次不新增 WebUI；`api_version` 约束不适用。

---

### Task 1: Cookie 新路径与兼容查找

**Files:**
- Create: `tests/test_cookie_lookup.py`
- Modify: `fc2cmadb_crawler/config.py`
- Modify: `fc2cmadb_crawler/crawler.py`

**Interfaces:**
- Consumes: `PROJECT_ROOT`、`COOKIE_FILENAME`、`SCRIPT_DIR`
- Produces: `SECRETS_DIR: str`；`find_cookie_file(filename: str = COOKIE_FILENAME) -> str | None`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_cookie_lookup.py`，使用 `tempfile.TemporaryDirectory` 和 `unittest.mock.patch` 隔离三个候选目录：

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from fc2cmadb_crawler import crawler


class FindCookieFileTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.secrets_dir = self.base / "secrets"
        self.cwd = self.base / "cwd"
        self.project_root = self.base / "project"
        for path in (self.secrets_dir, self.cwd, self.project_root):
            path.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def find_cookie(self):
        with (
            patch.object(crawler, "SECRETS_DIR", str(self.secrets_dir)),
            patch.object(crawler, "SCRIPT_DIR", str(self.project_root)),
            patch.object(crawler.os, "getcwd", return_value=str(self.cwd)),
        ):
            return crawler.find_cookie_file("cookies.txt")

    def test_prefers_secrets_directory(self):
        secret = self.secrets_dir / "cookies.txt"
        secret.write_text("secret", encoding="utf-8")
        (self.cwd / "cookies.txt").write_text("cwd", encoding="utf-8")
        (self.project_root / "cookies.txt").write_text("root", encoding="utf-8")
        self.assertEqual(self.find_cookie(), str(secret.resolve()))

    def test_falls_back_to_legacy_project_root(self):
        legacy = self.project_root / "cookies.txt"
        legacy.write_text("root", encoding="utf-8")
        self.assertEqual(self.find_cookie(), str(legacy.resolve()))

    def test_returns_none_when_no_cookie_exists(self):
        self.assertIsNone(self.find_cookie())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```powershell
python -m unittest discover -s tests -p "test_cookie_lookup.py" -v
```

Expected: `test_prefers_secrets_directory` 失败，原因是 `crawler` 尚无 `SECRETS_DIR`。

- [ ] **Step 3: 添加最小实现**

在 `fc2cmadb_crawler/config.py` 中、`SCRIPT_DIR` 后增加：

```python
SECRETS_DIR = str(PROJECT_ROOT / "secrets")
```

在 `fc2cmadb_crawler/crawler.py` 的配置导入列表中加入 `SECRETS_DIR`，并将候选路径改为：

```python
def find_cookie_file(filename=COOKIE_FILENAME):
    """优先读取 secrets，其次兼容当前启动目录和项目根目录。"""
    candidates = [
        os.path.join(SECRETS_DIR, filename),
        os.path.join(os.getcwd(), filename),
        os.path.join(SCRIPT_DIR, filename),
    ]
    existing_paths = unique_existing_paths(candidates)
    return existing_paths[0] if existing_paths else None
```

同时把未找到 Cookie 的用户提示改为 `secrets/{COOKIE_FILENAME}`。

- [ ] **Step 4: 运行测试并确认通过**

Run:

```powershell
python -m unittest discover -s tests -p "test_cookie_lookup.py" -v
```

Expected: 3 tests pass.

- [ ] **Step 5: 提交**

```powershell
git add tests/test_cookie_lookup.py fc2cmadb_crawler/config.py fc2cmadb_crawler/crawler.py
git commit -m "feat: load cookies from secrets directory"
```

---

### Task 2: 隐私文件、忽略规则与文档

**Files:**
- Move: `fc2cmadb.com_cookies.txt` → `secrets/fc2cmadb.com_cookies.txt`
- Create: `secrets/fc2cmadb.com_cookies.txt.example`
- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Task 1 的 `SECRETS_DIR` 和 Cookie 查找顺序
- Produces: 真实 Cookie 与脱敏 `.example` 的固定目录结构；仅含两个目录规则的 `.gitignore`

- [ ] **Step 1: 验证移动目标**

Run:

```powershell
Test-Path -LiteralPath 'fc2cmadb.com_cookies.txt'
Test-Path -LiteralPath 'secrets\fc2cmadb.com_cookies.txt'
```

Expected: 源文件为 `True`，目标文件为 `False`；若目标已存在则停止，避免覆盖。

- [ ] **Step 2: 创建目录并移动真实文件**

```powershell
New-Item -ItemType Directory -Path 'secrets' -Force
Move-Item -LiteralPath 'fc2cmadb.com_cookies.txt' -Destination 'secrets\fc2cmadb.com_cookies.txt'
```

- [ ] **Step 3: 创建脱敏示例**

创建 `secrets/fc2cmadb.com_cookies.txt.example`：

```text
# Netscape HTTP Cookie File
# 复制本文件为 fc2cmadb.com_cookies.txt，或使用浏览器插件导出后覆盖目标文件。
# 字段依次为：domain、include_subdomains、path、secure、expiry、name、value。
.example.invalid	TRUE	/	TRUE	0	age_pass	REPLACE_WITH_EXPORTED_VALUE
.example.invalid	TRUE	/	TRUE	0	session	REPLACE_WITH_EXPORTED_VALUE
```

- [ ] **Step 4: 收敛 `.gitignore`**

将 `.gitignore` 完整内容改为：

```gitignore
output/
~temp/
```

- [ ] **Step 5: 更新 README**

把 Cookie 保存路径改为 `secrets/fc2cmadb.com_cookies.txt`；说明 `.example` 的复制/导出方式和含真实隐私历史的分支不得直接推送。更新目录结构，标明：

```text
secrets/    本地真实隐私配置及脱敏示例
output/     生成输出，不提交
~temp/      临时文件，不提交
~archived/  归档内容，本地提交
~ref/       参考项目，本地提交
```

- [ ] **Step 6: 更新 CHANGELOG**

在文件顶部新增 `2026-07-26` 条目，记录：

- Cookie 移入 `secrets/` 并保留旧位置兼容；
- 新增脱敏 `.example`；
- `.gitignore` 仅保留 `output/` 与 `~temp/`；
- 其余内容改为本地完整跟踪；
- 当前含隐私分支不得直接推送。

- [ ] **Step 7: 验证隐私文件与文档**

Run:

```powershell
Test-Path -LiteralPath 'secrets\fc2cmadb.com_cookies.txt'
Test-Path -LiteralPath 'secrets\fc2cmadb.com_cookies.txt.example'
git diff --check
```

Expected: 两个路径均为 `True`，`git diff --check` 无输出。比较真实文件和示例文件的非注释值，确认示例不包含真实 Cookie 值，但不得在终端输出真实值。

- [ ] **Step 8: 提交**

```powershell
git add .gitignore README.md CHANGELOG.md secrets/fc2cmadb.com_cookies.txt secrets/fc2cmadb.com_cookies.txt.example
git commit -m "chore: align repository privacy layout"
```

---

### Task 3: 完整本地跟踪与最终验证

**Files:**
- Create: `.gitmodules`
- Add: `~ref/grill-with-docs`
- Add: `.vscode/`
- Add: `__pycache__/`
- Add: `fc2cmadb_crawler/__pycache__/`
- Add: `~archived/`
- Add: 除 `output/`、`~temp/` 外的其他现有未跟踪内容

**Interfaces:**
- Consumes: Task 2 的 `.gitignore`
- Produces: 无遗漏的本地 Git 跟踪状态和固定版本的参考仓库

- [ ] **Step 1: 将参考仓库登记为 Git 引用**

对已克隆的目录执行：

```powershell
git submodule add --force https://github.com/mattpocock/skills.git '~ref/grill-with-docs'
```

Expected: 生成 `.gitmodules`，并把 `~ref/grill-with-docs` 登记为固定提交的 Git 引用。

- [ ] **Step 2: 检查待跟踪范围**

Run:

```powershell
git status --short --ignored
```

Expected: 只有 `output/` 和存在时的 `~temp/` 显示为 ignored；其他内容显示为已跟踪修改或未跟踪。

- [ ] **Step 3: 运行完整代码验证**

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py fc2cmadb_crawler tests
```

Expected: 所有测试通过，Python 编译检查退出码为 0。

- [ ] **Step 4: 暂存并检查其余非输出内容**

Run:

```powershell
git add -A
git diff --cached --check
git status --short --ignored
```

Expected:

- diff 检查无输出；
- 除 `output/`、`~temp/` 外没有未跟踪或被忽略内容。
- 暂存清单不存在 `output/`、`~temp/`，且真实 Cookie 位于 `secrets/`。

- [ ] **Step 5: 提交完整跟踪状态**

```powershell
git commit -m "chore: track complete local repository state"
```

- [ ] **Step 6: 提交后复核**

Run:

```powershell
git status --short --branch --ignored
git log -5 --oneline --decorate
```

Expected: 工作树除 `output/`、`~temp/` 的 ignored 提示外保持干净；最新提交包含完整跟踪状态。不得运行 `git push`。
