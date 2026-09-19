# Agent Context

## 技术架构

项目是 Python 命令行应用。`fc2cmadb_crawler/main.py` 调用同包 `crawler.main()`；爬虫通过独立的持久 Chrome profile 与目标站点交互，解析页面后在 `~outputs/` 创建目录和 `.url` 文件。`tools/` 是独立辅助工具包，包含非媒体文件复制、快捷方式域名修复及对应 Windows 批处理入口。

## 项目结构

- `fc2cmadb_crawler/`：应用实现与集中配置。
- `tools/`：独立辅助工具及其 Windows 批处理入口。
- `tests/`：不访问网络的 `unittest` 测试。
- 独立 Chrome profile：位于 `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`，仅保存本机浏览器登录状态，不属于项目文件或 Git。
- `reference/grill-with-docs/`：固定到完整 SHA 的只读 Git submodule；版本和重建方式见 [reference/README.md](reference/README.md)。
- `~archive/`：保留的旧版本和审计材料，不含真实 secret。
- `~outputs/`、`~temp/`：不进入 Git 的生成结果与临时内容。

## 开发流程

行为变更先添加离线测试，再修改实现。常用验证命令：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q fc2cmadb_crawler tools tests
```

`tests/test_persistent_browser_profile.py` 覆盖持久 Chrome profile 的启动参数和 Inertia 登录态判断；测试不启动真实 Chrome。

真实站点抓取依赖本机 Chrome、用户手动登录的持久 profile 和目标站点可用性，不属于自动化验证。依赖变更更新 `requirements.txt`；公开行为或安装使用变化更新 README；所有用户可见变更更新 CHANGELOG。

## 已知问题

- Chrome、Cloudflare 和目标站点页面结构属于外部不稳定依赖；离线测试不能证明真实抓取仍可用。
