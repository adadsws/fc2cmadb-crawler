# 包入口迁移计划

## 需求

根目录不再保留 `main.py`。现有爬虫启动能力、Windows 双击启动方式和手动
指定 `CHROME_VERSION_MAIN` 的方式保持可用，自动化验证不得访问网络或启动
Chrome。同时从远程当前 `main` 删除完整的 `~archive/` 树，本地归档保持不动。
远程当前 `main` 还需删除 `reference/`、`.vscode/`；`reference/` 是 submodule，
因此远端 `.gitmodules` 也随之删除。本地这些路径及其内容均保持不变。

## 设计

### 入口位置决策

- [x] 按用户指定，将薄入口移动为 `fc2cmadb_crawler/main.py`，统一使用
  `python -m fc2cmadb_crawler.main`。不保留根目录 `main.py`，也不新增包级
  `__main__.py`。

### 远程专用目录删除范围决策

- [x] **A（已确认）**：在 `~temp/github-export/` 脱敏导出仓库中删除当前
  `main` 的整个 `~archive/`、`reference/`、`.vscode/` 和失去作用的
  `.gitmodules`，创建普通 fast-forward commit。远程当前文件树不再显示这些
  路径，但旧提交历史仍保留历史对象；本地对应路径不变。
- [ ] **B**：从远程全部历史彻底清除上述路径。这需要停止写入、记录全部
  refs、在隔离克隆中使用固定版 `git-filter-repo`、再次批准远程历史改写并
  force push，不属于本计划的普通发布流程。

用户回复 `v` 时采用 A；只有明确回复 `历史改写` 才会停止本计划，并另建历史
清理计划走二次批准。

## 实施

采用已确认的包内 `main.py` 入口时：

1. 先新增离线测试 `tests/test_package_entrypoint.py`，用 mock 替换
   `fc2cmadb_crawler.crawler.main()`，通过 `runpy` 验证包入口调用一次并透传
   `SystemExit` 返回码，不启动 Chrome。
2. 将根目录 `main.py` 原样移动为 `fc2cmadb_crawler/main.py`。
3. 将 `run_fc2cmadb_crawler.bat` 改为运行
   `"%PYTHON_EXE%" -m fc2cmadb_crawler.main`。
4. 将 README 中两处 `python main.py`、目录树和 Chrome 版本示例改为包入口。
5. 更新 `AGENT_CONTEXT.md` 的架构说明和编译检查命令。
6. 在 `CHANGELOG.md` 新增 `2026-08-05` 条目，记录根入口迁移和新启动命令。
7. 检查根目录不存在 `.py` 文件，且项目中没有现行文档或脚本继续引用根
   `main.py`；历史 CHANGELOG 与已完成计划保留原始记录，不回写历史。
8. 本地提交完成后，将远程 `main` 克隆到 `~temp/github-export/`，只复制允许
   发布的源码、测试和文档；不得复制本地 `~archive/`、`~outputs/`、真实
   secret、`reference/`、`.vscode/` 或私有历史。
9. 在导出仓库逐一解析并确认目标都位于导出目录后，执行
   `git rm -r -- ~archive reference .vscode`，并移除因 submodule 删除而失去
   作用的 `.gitmodules`；同时删除远程根 `main.py`，加入
   `fc2cmadb_crawler/main.py` 及其他本次公开修改。
10. 检查导出差异、提交历史、隐私、离线测试和 `pre-push` hook；仅在远程
    没有新增提交时 fast-forward push `main`。

## 测试

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -v
python -m compileall -q fc2cmadb_crawler tests
```

额外验证：

- 新入口测试必须在 mock 下运行，不访问 `fc2cmadb.com`、不启动 Chrome。
- `run_fc2cmadb_crawler.bat` 只调用包入口。
- README 与 `AGENT_CONTEXT.md` 不再把根 `main.py` 当作当前入口。
- 根目录无 `.py` 文件。
- 工作树只包含本计划列出的相关修改和计划移动。
- 导出仓库暂存区删除 `~archive/`、`reference/`、`.vscode/` 的全部已跟踪路径
  以及 `.gitmodules`，且不新增任何相同前缀路径。
- 远程 push 后当前 `main` 树中不存在 `~archive/`、`reference/`、`.vscode/`
  和 `.gitmodules`，远程分支仍只有 `main`。
- 本地 `~archive/`、`reference/`、`.vscode/` 和 `.gitmodules` 的数量与内容
  不因远程删除而改变。

## 完成

实施、测试和验证通过后，将本计划移动到
`docs/finished_plans/2026-08-05-package-entrypoint.md`，创建本地 Git commit；
随后通过 `~temp/github-export/` 创建脱敏发布 commit，并 fast-forward push
远程 `main`。不创建其他分支、PR，不 force push。
