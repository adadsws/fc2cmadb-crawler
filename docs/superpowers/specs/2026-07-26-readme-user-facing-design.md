# README 用户文档收敛设计

## 目标

README 只面向安装和使用项目的最终用户，不承载 `AGENTS.md` 中的内部
Git 跟踪、归档、脱敏导出和发布流程。

## 保留内容

- 项目用途、功能、安装方式和依赖。
- `secrets/fc2cmadb.com_cookies.txt` 的用户配置路径。
- `secrets/fc2cmadb.com_cookies.txt.example` 的复制与填写方式。
- 爬虫和两个工具的启动命令、参数与交互说明。
- 目录树中的源码、启动脚本、依赖、CHANGELOG、`secrets/`、
  `recommend_20260629/` 和 `output/`。

## 移除内容

- Cookie 章节中关于真实 Cookie 进入本地 Git、源仓库不得直接 push 和
  只发布 `.example` 的内部说明。
- 整个“脱敏发布”章节。
- 目录树中的 `~ref/`、`~archived/` 和 `~temp/`。
- `secrets/` 目录注释中的“本地提交”措辞。
- 其他只用于执行 `AGENTS.md`、不帮助最终用户安装或运行程序的内容。

## 修改后的文案

Cookie 章节在 `.example` 配置说明后直接进入“运行爬虫”，不再插入仓库
维护或发布流程。

目录树中的相关部分为：

```text
├── CHANGELOG.md
├── secrets/                   # Cookie 配置与脱敏示例
├── recommend_20260629/
└── output/                    # 生成输出
```

## 验证

- README 不包含 `AGENTS.md`、`~ref/`、`~archived/`、`~temp/`、
  `github-export`、`fast-forward`、`pre-push`、`force push` 或
  “脱敏发布”。
- README 仍包含 `secrets/fc2cmadb.com_cookies.txt`、
  `secrets/fc2cmadb.com_cookies.txt.example`、`python main.py` 和
  `output/`。
- 仅修改 README 文案，不改变程序、测试、配置或发布流程。
- 修改完成后运行 Markdown 空白检查并创建本地 Git commit；不自动 push。
