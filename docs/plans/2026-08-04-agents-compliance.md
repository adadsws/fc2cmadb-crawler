# 全局 AGENTS.md 严格合规整改计划

## 需求与成功标准

目标是让当前项目满足 2026-08-04 提供的全局 `AGENTS.md`，包括文件布局、文档职责、Git 跟踪、上游引用、secret 加密、历史清理、验证和提交要求。成功标准如下：

- 根目录只保留必要入口、批处理、项目文档和生态配置；源码继续位于 `fc2cmadb_crawler/`。
- 运行输出、临时文件、归档、上游参考和真实 secret 分别位于 `~outputs/`、`~temp/`、`~archive/`、`reference/` 和 `secrets/`。
- `README.md`、`CHANGELOG.md`、`AGENT_CONTEXT.md`、项目根 `AGENTS.md` 职责清晰且内容不重复。
- 除规则明确排除的内容外，项目文件均由本地 Git 跟踪；已生成的 Python 缓存不再被跟踪。
- 所有真实 secret 都在 `secrets/**`，Git index 与 commit 中只记录 `git-crypt` 密文，`.example` 保持明文且不含真实值。
- 本地相关 Git 历史不再包含旧 Cookie 文件或真实 Cookie 值；远程历史改写、旧对象清理和要求协作者重新克隆在执行前再次确认。
- 自动化测试、编译、路径、文档、submodule、Git 属性、密文 blob、敏感值扫描和工作树检查全部通过。
- 本计划先在 `docs/plans/` 提交；整改完成后移至 `docs/finished_plans/` 并提交。

## 已确认决策

- 采用严格一次性整改，不采用仅向前加密或拆分为两个不完整阶段。
- 包含 Cookie 轮换和所有本地相关 Git 历史的真实值清理。
- `git-crypt` 密钥、历史改写前备份、隔离完整克隆和审计材料统一放在 `C:\Users\Administrator\.config\git-crypt`。
- 用户明确要求使用上述系统盘目录，因此将其作为“离线加密介质”规则的显式例外；不得把其中内容复制进项目、Git、同步盘、日志或 `~outputs/`。
- 本次不自动 push、不自动改写远程历史、不创建固定副本；这些动作若成为完成严格合规所必需，将在执行到对应关口时再次确认。
- 不运行真实网站爬取；验证只使用离线测试和静态检查。

## 当前差距

- 缺少项目根 `AGENTS.md`、`AGENT_CONTEXT.md` 和 `.gitattributes`。
- 现有路径使用 `~archived/`、`~ref/` 和 `output/`，与全局规则指定的 `~archive/`、`reference/` 和 `~outputs/` 不一致。
- `__pycache__/`、`fc2cmadb_crawler/__pycache__/` 和 `tests/__pycache__/` 已被 Git 跟踪。
- `secrets/fc2cmadb.com_cookies.txt` 和多个归档 Cookie 已被明文提交；本地历史存在真实 secret，且 `git-crypt` 未安装或初始化。
- `git-filter-repo` 未安装；当前 Python 为 3.14.2，Git for Windows 为 2.38.0。
- `main` 相对 `origin/main` 为 ahead 16、behind 3，必须在历史处理前记录和审计双方 refs，不能直接合并或 push。
- `reference/grill-with-docs` 的前身是固定到 `ed37663cc5fbef691ddfecd080dff42f7e7e350d` 的 submodule，但缺少独立的许可证和重建说明。

## 设计

### 文件布局

- 将 `output/` 的现有内容完整移动到 `~outputs/`，并把 `fc2cmadb_crawler/config.py` 的 `OUTPUT_DIR` 改为该路径。
- 将 `~archived/` 改为 `~archive/`；其中真实 Cookie 保持相对归档语义移动到 `secrets/archive/`，非 secret 归档保留在 `~archive/`。
- 将 `~ref/grill-with-docs` 改为 `reference/grill-with-docs`，同步更新 `.gitmodules`，并新增 `reference/README.md` 记录 URL、完整 SHA、许可证、选择 submodule 的原因和重建命令。
- 删除空的 `docs/superpowers/` 目录；计划只使用 `docs/plans/` 和 `docs/finished_plans/`。
- 不删除用户数据；路径迁移前后按文件数与总字节数核对。

### Git 跟踪与文档

- `.gitignore` 仅加入已经实际产生且规则允许忽略的路径：`~outputs/`、`~temp/`、`.venv/`、`.worktrees/`、根及相邻包/测试目录的 `__pycache__/`。每条缓存规则旁写明对应生成器。
- 用 `git rm --cached` 取消跟踪缓存，但保留工作树文件；其他项目文件继续跟踪。
- `AGENTS.md` 只记录本项目特有约束：离线测试、不在验证中访问目标站点、输出目录和 Cookie 示例维护要求。
- `AGENT_CONTEXT.md` 记录架构、包结构、开发测试流程、submodule 和已知问题，不复制 README 使用说明。
- README 更新安装、运行、目录和 secret 使用说明；CHANGELOG 新增 `2026-08-04` 节，记录结构、隐私与兼容性变更。

### Secret 与历史

- `.gitattributes` 使用以下优先级：`secrets/** filter=git-crypt diff=git-crypt`，随后对 `*.example`、`*.example.*` 的四种指定层级模式配置 `!filter !diff`。
- 使用固定的 `git-crypt 0.7.0`；使用固定的 `git-filter-repo 2.47.0`，安装在 `~temp/history-tools/` 的可重建环境中。下载或安装需要网络时单独请求权限，并记录版本与 SHA-256，不把二进制提交到项目。
- 用户先在目标站点撤销旧会话并重新导出 Cookie；验证新文件路径后再继续。终端不得显示 Cookie 正文。
- 在外部目录创建时间戳子目录，保存加密完整备份、全部 branch/tag/worktree/commit 清单、工具版本和脱敏审计报告；备份加密口令不得写入仓库或日志。
- 从本地仓库创建包含全部 refs 的隔离完整克隆。对独立 Cookie 路径执行 `--sensitive-data-removal --invert-paths --path ...`，并使用仓库外 `--replace-text` 规则清理曾出现在其他文件中的真实值。
- 在隔离克隆中恢复当前所需 secret 到 `secrets/**`，初始化 `git-crypt`，导出密钥到外部目录，并执行 `git add --renormalize secrets`。
- 清理后扫描 refs、stash、reflog、对象和已知远程 refs。只有隔离克隆验证通过，才提出“替换当前仓库旧对象库/清理旧对象”的再次确认；只有远程平台仍含真实值且用户再次批准，才设计并执行远程历史改写。

## 实施步骤

### 1. 建立安全基线

1. 记录 `git status --short --branch`、全部本地与远程 refs、tag、stash、worktree、submodule SHA 和当前提交。
2. 检查工作树仍无计划文件之外的改动；如出现用户改动，停止并重新划分提交范围。
3. 验证 `C:\Users\Administrator\.config\git-crypt` 的解析后绝对路径不位于项目内；创建本次专用子目录，不覆盖已有文件。
4. 创建加密完整备份并验证可读取；只在脱敏报告中记录校验值。
5. 提示用户完成旧 Cookie 会话撤销与新 Cookie 导出；在用户确认轮换完成前不进行历史替换。

### 2. 用测试锁定路径变更

1. 在 `tests/test_config_paths.py` 添加测试，断言 `OUTPUT_DIR == PROJECT_ROOT / "~outputs"` 且所有真实 secret 根目录为 `PROJECT_ROOT / "secrets"`。
2. 扩充 `tests/test_cookie_lookup.py`，确认新 secret 优先、旧根路径仅作兼容、缺失返回 `None`，且诊断文案不包含 secret 值。
3. 运行 `python -m unittest discover -s tests -v`，确认新输出路径测试先失败。
4. 修改 `fc2cmadb_crawler/config.py` 的 `OUTPUT_DIR`，运行测试确认通过。

### 3. 迁移目录且保留数据

1. 分别统计 `output/`、`~archived/`、`~ref/` 的文件数和总字节数，保存脱敏统计。
2. 使用同一 PowerShell 会话和显式 `-LiteralPath` 逐项移动到 `~outputs/`、`~archive/`、`reference/`；目标已存在时停止，不合并覆盖。
3. 把 `~archive/` 内所有真实 Cookie 移到 `secrets/archive/` 的对应相对路径，保留 `.example`，并确认 `~archive/` 不再存在真实 secret。
4. 更新 `.gitmodules` 的名称和路径，确认 gitlink 仍固定到 `ed37663cc5fbef691ddfecd080dff42f7e7e350d`。
5. 对迁移前后文件数、字节数和抽样哈希进行核对；不删除原始数据的唯一副本。

### 4. 整理跟踪规则与文档

1. 更新 `.gitignore`，取消跟踪但不删除三个范围内已生成的 `__pycache__` 文件。
2. 新增 `.gitattributes`、根 `AGENTS.md`、`AGENT_CONTEXT.md` 和 `reference/README.md`。
3. 更新 README 的输出路径、目录结构、安装/运行和 Cookie 指引；更新 CHANGELOG 的 `2026-08-04` 节。
4. 搜索活动文档与源码中的 `~archived`、`~ref`、`output/` 旧引用，仅保留 CHANGELOG 历史叙述中确有必要的旧名称。
5. 运行 `git diff --check`、Markdown 路径检查和全量单元测试。

### 5. 加密当前 secret

1. 获取并验证固定版本 `git-crypt 0.7.0`，确认 `git-crypt --version`。
2. 先提交 `.gitattributes`，再执行 `git-crypt init`；将密钥导出到外部专用目录。
3. 执行 `git add --renormalize secrets`，用 `git check-attr` 验证真实 secret 使用 filter/diff，所有 `.example` 均显式取消 filter/diff。
4. 使用 blob 类型、大小、熵/头部特征和 `git-crypt status` 验证真实 secret 的 index blob 已加密；只报告布尔结果与哈希，不输出正文。
5. 验证 `.example` 为明文结构且不包含真实 Cookie 值。

### 6. 清理并验证本地历史

1. 获取并验证固定版本 `git-filter-repo 2.47.0`，在隔离完整克隆中先演练一次。
2. 移除全部已知当前及旧 Cookie 路径；再用外部替换规则处理其他文件中的真实值。
3. 检查全部 refs、stash、reflog、对象和远程跟踪 refs；生成不含真实值的审计报告。
4. 恢复轮换后的当前 Cookie，用 `git-crypt` 加密并提交；确认历史中首次出现该文件即为密文 blob。
5. 向用户展示验证摘要，并再次请求是否用已验证的清理仓库替换当前旧对象库、是否清理旧对象、是否改写远程历史。未获确认时保留安全备份和隔离克隆，不执行这些破坏性动作。

### 7. 最终验证与提交

1. 运行 `python -m unittest discover -s tests -v`。
2. 运行 `python -m compileall -q main.py fc2cmadb_crawler tests`，确认退出码为 0。
3. 检查所有忽略项都有规则依据，除允许项外无未跟踪/忽略内容，根目录布局符合规则。
4. 检查 submodule URL、完整 SHA、许可证与重建说明。
5. 检查 README、CHANGELOG、AGENT_CONTEXT 和 AGENTS 职责与链接，无重复大段内容。
6. 检查 Git diff、暂存区、历史和密文 blob，不显示 secret 正文。
7. 提交仅包含本次相关改动；不纳入无关用户改动，不 push。
8. 将本计划移动到 `docs/finished_plans/2026-08-04-agents-compliance.md`，再次运行文档和工作树检查并提交归档。

## 测试矩阵

| 范围 | 方法 | 通过标准 |
|---|---|---|
| Cookie 查找 | `unittest` | 新路径优先、旧路径兼容、缺失安全失败 |
| 输出路径 | 配置单元测试 | 解析为项目根下 `~outputs/` |
| Python | `unittest` + `compileall` | 全部退出码为 0 |
| 数据迁移 | 数量、字节数、抽样哈希 | 迁移前后一致且无覆盖 |
| Git 跟踪 | `status`、`ls-files`、`check-ignore` | 仅规则允许内容被忽略，缓存不再跟踪 |
| Secret 属性 | `check-attr`、`git-crypt status` | 真实文件加密，example 明文 |
| Secret blob | index/commit blob 检查 | 无明文正文或已知真实值 |
| 历史 | refs/stash/reflog/object 扫描 | 本地相关历史无真实值 |
| 上游引用 | gitlink 与说明核对 | URL、SHA、许可证、重建方法完整 |
| 文档 | 链接、路径与职责检查 | 无失效路径、无职责重复 |

## 失败与回退

- 任一移动目标已存在、统计不一致或哈希不一致：立即停止，保持源数据，不合并覆盖。
- 依赖下载、版本或 SHA-256 无法验证：不执行 secret/history 操作。
- 新 Cookie 未完成轮换：只完成非破坏性的结构与测试工作，不替换历史。
- 隔离克隆仍命中真实值：保留原仓库和加密备份，修正规则后重新演练。
- `git-crypt` 属性或 blob 验证失败：不提交真实 secret，恢复到已验证备份。
- 当前仓库替换、旧对象清理或远程改写未获再次确认：停止在已验证隔离克隆阶段，并明确报告尚未满足的最后条件。

## 最终确认清单

批准本计划即授权执行非远程、可回退的整改步骤及必要的固定版本工具安装。以下三项不由本次批准自动授权，执行到关口时必须再次确认：

- [ ] 用清理后的隔离仓库替换当前仓库的旧 Git 对象库。
- [ ] 清理备份之外仍含旧 secret 的本地对象、reflog 或临时克隆。
- [ ] 改写远程历史、force push，或要求协作者重新克隆。
