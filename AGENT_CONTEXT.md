# Agent Context

## 技术架构

项目是 Python 命令行应用。`main.py` 调用 `fc2cmadb_crawler.crawler.main()`；爬虫通过 Chrome 与目标站点交互，解析页面后在 `~outputs/` 创建目录和 `.url` 文件。`copy_non_media.py` 与 `shortcut_domains.py` 提供两个独立的文件工具，薄入口分别位于同包的 `copy_non_media_files.py` 和 `update_shortcut_domains.py`。

## 项目结构

- `fc2cmadb_crawler/`：应用实现与集中配置。
- `tests/`：不访问网络的 `unittest` 测试。
- `secrets/`：由 `git-crypt` 保护的真实 Cookie、归档 secret 及明文脱敏示例。
- `reference/grill-with-docs/`：固定到完整 SHA 的只读 Git submodule；版本和重建方式见 [reference/README.md](reference/README.md)。
- `~archive/`：保留的旧版本和审计材料，不含真实 secret。
- `~outputs/`、`~temp/`：不进入 Git 的生成结果与临时内容。

## 开发流程

行为变更先添加离线测试，再修改实现。常用验证命令：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q main.py fc2cmadb_crawler tests
```

真实站点抓取依赖本机 Chrome、有效登录 Cookie 和目标站点可用性，不属于自动化验证。依赖变更更新 `requirements.txt`；公开行为或安装使用变化更新 README；所有用户可见变更更新 CHANGELOG。

## 已知问题

- `main` 与 `origin/main` 存在本地/远程分叉，完成历史清理前不得直接 push。
- Chrome、Cloudflare 和目标站点页面结构属于外部不稳定依赖；离线测试不能证明真实抓取仍可用。
