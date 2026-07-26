# 全局 AGENTS.md 合规整改设计

## 背景与目标

当前仓库的 `.gitignore` 除 `output/` 外还排除了编辑器配置、Python 缓存、真实 Cookie、归档目录等内容，不符合全局 `AGENTS.md` 对本地 Git 跟踪范围的要求。真实 Cookie 也位于项目根目录，且缺少对应的脱敏示例文件。

本次整改的目标是：

- `output/` 只保存输出，`~temp/` 只保存临时文件，并且仅这两个目录通过 `.gitignore` 排除。
- 真实隐私配置集中放在 `secrets/`，每个真实隐私文件都有保留格式和说明的 `.example`。
- 除 `output/`、`~temp/` 之外，当前仓库内容全部进入本地 Git 跟踪。
- 保持现有 Cookie 配置的向后兼容，不丢失用户数据。
- 更新使用文档与变更记录，并创建本地 Git 提交。
- 含真实隐私数据的当前分支不得直接推送。
- 归档并移除旧的脱敏导出分支，使源仓库只保留 `main`。
- 发布只允许通过 `output/github-export/` 中的独立脱敏导出仓库完成。

## 文件与跟踪策略

`.gitignore` 仅保留以下两项：

```gitignore
output/
~temp/
```

现有 `.vscode/`、`__pycache__/`、`fc2cmadb_crawler/__pycache__/`、`~archived/` 和其他非输出内容都纳入本地 Git。`~ref/grill-with-docs` 作为本次规范化工作的参考仓库，以可追踪其来源和固定版本的 Git 引用方式纳入当前仓库。

不会删除任何文件。真实 Cookie 从根目录移动到 `secrets/`，属于保留内容的位置调整。

已经完成的实施计划从 `docs/superpowers/plans/` 移入
`~archived/superpowers-plans/`。设计规格继续保留在
`docs/superpowers/specs/`，用于说明整改依据。

## 旧导出分支归档

本地分支 `codex/sanitized-export-20260726` 不符合源仓库仅保留
`main` 的最终状态。移除分支前，先将该分支制作成：

```text
~archived/git-branches/sanitized-export-20260726.bundle
```

归档必须包含原分支 tip，并通过 `git bundle verify` 与引用检查。
只有归档验证成功后才允许删除本地分支。bundle 由本地 Git 记录，
但不得复制到脱敏导出仓库或推送到远程。

## 隐私配置结构

真实文件路径：

```text
secrets/fc2cmadb.com_cookies.txt
```

脱敏示例路径：

```text
secrets/fc2cmadb.com_cookies.txt.example
```

示例文件保留 Netscape Cookie 文件的结构、字段顺序和中文配置说明，但不包含当前真实 Cookie 的域名、令牌或会话值。

真实文件与示例文件都进入本地 Git 提交。由于提交历史包含真实隐私值，
当前仓库和分支不得直接推送。发布时必须使用
`output/github-export/` 中的独立脱敏导出仓库，并只携带 `.example`；
不再使用 orphan 分支作为发布方式。

## Cookie 查找行为

配置层提供 `secrets/` 下的新默认 Cookie 路径。Cookie 查找顺序为：

1. `secrets/fc2cmadb.com_cookies.txt`；
2. 调用方当前工作目录中同名 Cookie 文件的旧位置；
3. 项目根目录中同名 Cookie 文件的旧位置。

新位置优先，旧位置仅用于兼容现有调用方式。未找到 Cookie 时，控制台提示和 README 都指向 `secrets/` 下的新位置。

## 文档

README 更新以下内容：

- Cookie 文件应放入 `secrets/`；
- 可复制 `.example` 后填写真实值；
- 当前本地分支包含真实隐私时不得直接推送；
- 目录结构包含 `secrets/`、`~ref/`、`~archived/`、`output/` 和 `~temp/` 的职责。

CHANGELOG 新增 2026-07-26 条目，记录隐私文件结构、Cookie 查找兼容、Git 跟踪策略和参考仓库。

README 同时记录以下唯一允许的发布流程：

1. 将远程 `main` 克隆到 `output/github-export/`；
2. 仅复制允许发布的文件，以本地版本覆盖同路径内容；
3. 用脱敏示例替代 `data/` 中的隐私输入，省略 `~archived/`、`~ref/`
   和真实 `secrets/**`；
4. 对不适合推送的大目录以同名 Markdown 文件说明用途、来源和重建方法；
5. 检查待发布内容、提交历史和隐私，运行测试及 pre-push hook；
6. 远程更新时先同步，只对 `main` 执行 fast-forward push；
7. push 后确认源仓库、导出仓库和远程都只有 `main`。

## 验证

自动化测试覆盖：

- `secrets/` 中的新 Cookie 文件优先于旧位置；
- 新位置缺失时仍能找到旧根目录 Cookie；
- 所有候选位置缺失时返回未找到。

项目级验证包括：

- 运行自动化测试；
- 编译检查所有 Python 源文件；
- 检查 `.gitignore` 仅排除 `output/` 和 `~temp/`；
- 检查除上述两个目录外没有未跟踪或被忽略的仓库内容；
- 检查真实 Cookie 与 `.example` 同时存在；
- 检查 `.example` 不包含真实 Cookie 值；
- 检查 Git 提交成功且不执行远程推送。
- 检查旧导出分支已被有效 bundle 完整保存；
- 检查本地与远程分支列表只有 `main`；
- 检查已完成计划仅存在于 `~archived/superpowers-plans/`；
- 检查 README 不再建议 orphan 分支，并完整描述脱敏导出流程。

## 非目标

- 不改变爬虫抓取、目录生成或快捷方式处理逻辑。
- 不清理、删除或重写 `~archived/` 中的历史内容。
- 不发布、不推送，也不在本次整改中创建实际脱敏导出仓库。
- WebUI `api_version` 约束与当前非 WebUI 项目无关，不新增 WebUI 配置。
