# Agent Context

## 技术架构

项目是 Python 命令行应用。`fc2cmadb_crawler/main.py` 调用同包 `crawler.main()`；`fc2cmadb_crawler/browser.py` 启动或复用普通可见 Chrome，并通过本机调试端口附加 Selenium。解析页面后在 `~outputs/` 创建作品目录和唯一的演员级 `.url`。作品目录不创建网页快捷方式。`tools/` 是独立辅助工具包，包含非媒体文件复制、快捷方式域名修复及对应 Windows 批处理入口。

主程序在业务输入前优先从当前站内页确认登录；不能确认时最多访问一次准备页。输入由 `CrawlerTarget` 区分演员 ID 与纯数字 FC2 番号；FC2 模式访问 `/articles/{番号}`，要求从 Inertia 主作品数据或主内容演员链接解析出唯一演员 ID，再进入原有 `crawl_actress()`，不维护第二套目录创建流程。

## 项目结构

- `fc2cmadb_crawler/`：应用实现与集中配置。
- `tools/`：独立辅助工具及其 Windows 批处理入口。
- `tests/`：不访问网络的 `unittest` 测试。
- 独立 Chrome profile：位于 `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`，仅保存本机浏览器登录状态，不属于项目文件或 Git。
- `~archive/`：保留的旧版本和审计材料，不含真实 secret。
- `~outputs/`、`~temp/`：不进入 Git 的生成结果与临时内容。

## 开发流程

行为变更先添加离线测试，再修改实现。常用验证命令：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q fc2cmadb_crawler tools tests
```

`tests/test_persistent_browser_profile.py` 覆盖普通 Chrome 独立启动后附加、当前登录页复用、统一 CDP 导航、同 URL 跳过和退出只断开驱动；测试不启动真实 Chrome。

`tests/test_fc2_number_input.py` 覆盖数字键菜单、旧版直接演员 ID 兼容、FC2 详情 URL、唯一/多演员解析，以及登录准备早于业务输入。

`tests/test_shortcut_urls.py` 覆盖原有 `id_{演员ID} - latest_{最新番号}` 快捷方式名称，以及作品目录不创建 `.url`。

真实站点抓取依赖本机 Chrome、用户手动登录的持久 profile 和目标站点可用性，不属于自动化验证。依赖变更更新 `requirements.txt`；公开行为或安装使用变化更新 README；所有用户可见变更更新 CHANGELOG。

## 降低验证与挑战的统一方法

经两个爬虫项目的真实站点调试，核心原则是复用可信的普通浏览器会话，而不是反复制造新会话。`PersistentBrowser` 用项目专用持久 Profile 启动普通可见 Chrome，再从本机调试端口附加 Selenium；重新运行时优先复用仍存活的调试端口、当前页面、Cookie 和登录状态。CLI 退出只停止驱动服务，不关闭 Chrome。

所有 fc2cmadb 业务页必须调用 `PersistentBrowser.navigate()`；调用方禁止直接执行 `driver.get()`、`refresh()` 或自行创建 WebDriver。该入口跳过相同 URL、限制连续导航速率、通过 CDP `Page.navigate` 跳转，并在超时时调用 `Page.stopLoading`。演员第一页、后续分页、FC2 详情和准备页都遵守同一路径，且每个演员任务前不得重复访问首页。

挑战判断同时检查标题和可见正文，不得仅凭原始 HTML 中的 `cf-chl-widget` 或嵌入式 Turnstile iframe 判断整页挑战。入口先等待自动跳转，仅超时后提示用户在可见 Chrome 内处理；人工确认后等待现有页面解除挑战，不刷新页面。首次运行、用户关闭 Chrome、系统重启、Cookie 过期或站点策略变化后仍可能出现验证；代码不得绕过 CAPTCHA 或安全屏障。

FC2 详情页的 Inertia `article` 初始数据可能没有演员字段，演员链接由前端 hydration 稍后渲染。解析前必须等待“页面错误状态或可解析的数字演员链接”，不能只等待 `document.readyState=complete`。

姐妹项目 `leak` 对每个目标站点使用独立 Profile，并在同一受控入口内允许已经验证的 SupJav 会话同步 Cookie/UA 读取静态 HTML；只有明确 403/503 才回退可见浏览器。这里的单站项目不需要静态 HTTP 分支，但仍遵守“持久会话、单一导航入口、少访问首页、不刷新挑战页、退出不关 Chrome”的通用规则。

## 已知问题

- Chrome、Cloudflare 和目标站点页面结构属于外部不稳定依赖；离线测试不能证明真实抓取仍可用。
