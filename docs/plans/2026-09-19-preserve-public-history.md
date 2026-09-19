# 保留公开文件历史的 GitHub 发布计划

## 需求

- GitHub 必须能显示哪些公开文件在各次提交中未变、何时变更。
- 不发布 Cookie、归档、爬虫产物、缓存、原始输入或 `reference/` 内容。
- 保持当前公开源码、测试、文档和入口脚本可用。

## 方案

从当前本地源仓库创建一个不带工作树文件的临时 rewrite mirror；使用锁定版本的 `git-filter-repo` 对镜像执行白名单历史重写。白名单保留：

- 根目录的 `.gitignore`、`.gitattributes`、`AGENTS.md`、`AGENT_CONTEXT.md`、`CHANGELOG.md`、`README.md`、`requirements.txt`；
- 当前与历史根入口/工具脚本：`main.py`、`copy_non_media_files.py`、三个 `run_*.bat`；
- `docs/`、`fc2cmadb_crawler/`、`tests/` 与 `tools/`。

其余全部历史路径均不保留，因此 `secrets/`、`~archive/`、`reference/`、`recommend*`、`sample_output*`、缓存与任何其他生成内容不会出现在公开历史中。

## 实施与验证

- [ ] 在 `~temp/history-rewrite/` 创建仅本地使用的备份与 rewrite mirror，不继承到发布仓库。
- [ ] 验证锁定的 `git-filter-repo 2.47.0`，在 mirror 上按白名单重写全部历史。
- [ ] 对重写历史做路径审计、敏感赋值扫描、`git fsck`、工作树检查，并在导出副本运行离线测试。
- [ ] 核对当前公开文件内容与源仓库一致（仅允许为公开导出所需的忽略规则与无语义格式清理差异）。
- [ ] 将重写后的 `main` 以 `--force-with-lease` 推送到 GitHub，并重新核对远端 refs、提交和文件范围。
- [ ] 将本计划移至 `docs/finished_plans/`，提交源仓库的计划记录与必要的 `.gitignore` 更新；临时 mirror 保留在 `~temp/`，不发布。

## 一次性授权

确认本计划即授权我：

1. 在 `~temp/history-rewrite/` 创建仅本地的备份与 rewrite mirror，并用 `git-filter-repo` 重写 mirror 的历史；
2. 在审计和测试全部通过后，使用 `--force-with-lease` 再次替换 GitHub `main`，使其指向保留公开文件变更历史的重写提交；
3. 保留临时备份与 mirror，不执行不可逆的本地对象清理，也不删除任何远端 refs、tag 或仓库。
