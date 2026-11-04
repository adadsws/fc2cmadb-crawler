# Agent Context

<!-- 当前架构与验收规范；历史变更和任务证据分别见 CHANGELOG 与已完成 Plan。 -->

## 技术架构

项目是 Python 命令行应用。`fc2cmadb_crawler/main.py` 调用同包 `crawler.main()`；`fc2cmadb_crawler/browser.py` 启动或复用普通可见 Chrome，并通过本机调试端口附加 Selenium。解析页面后在 `~outputs/` 创建作品目录和唯一的演员级 `.url`。作品目录不创建网页快捷方式。`tools/` 包含只排除视频的文件复制、快捷方式域名修复、独立的 PowerShell 视频媒体信息重命名工具，以及与主程序共用 `fc2cmadb_crawler/naming.py` 命名规则的 FC2 目录更新工具；视频重命名通过 BAT 启动，并优先使用同目录的 `ffprobe.exe`。

主程序在业务输入前优先从当前站内页确认登录；不能确认时最多访问一次准备页。输入由 `CrawlerTarget` 区分演员 ID 与纯数字 FC2 番号；FC2 模式访问 `/articles/{番号}`，要求从 Inertia 主作品数据或主内容演员链接解析出唯一演员 ID，再进入原有 `crawl_actress()`，不维护第二套目录创建流程。

## 项目结构

- `fc2cmadb_crawler/`：应用实现与集中配置。
- `tools/`：辅助工具、FC2 目录维护工具及其 Windows 批处理入口。
- `tools/<工具名>/README.md` 与 `README_EN.md`：各工具文件夹表层的中英文用户说明；`tools/_shared/` 保存 Python 工具公共代码，根目录仅有 BAT 与文件夹。
- `tools/rename_vids/`：视频重命名工具的 PowerShell 脚本、FFprobe 固定版本说明与许可证；BAT 入口位于 `tools/` 根目录。本机 `ffprobe.exe` 不进入 Git，可由下载脚本重建。
- 交互入口先完成所需环境准备再显示选项：主爬虫准备 Chrome 与登录状态，FC2 文件夹工具附加项目 Chrome 并复用主程序的 `prepare_authenticated_session()` 确认登录状态，视频重命名工具定位 FFprobe；复制与快捷方式工具初始化控制台。FC2 文件夹工具带根目录的直接入口同样先确认登录；`--undo` 参数入口不需要 Chrome 或登录。
- 工具的数字菜单回车选择首项，路径输入不能靠回车执行；主程序与工具统一用 `b` 返回主菜单、`q` 退出；各工具可保持当前操作连续处理目录，并可按批次连续撤销原地修改。
- 三种原地修改工具按批次记录；撤销菜单以最近处理的文件夹路径列出未撤销批次，选定单批后预览和恢复。Python 工具历史在 `~outputs/undo-history/`，视频重命名历史在本地应用数据的 `VideoMediaRenamer/history/`，旧 `last-operation.json` 仅作为未撤销历史读取。
- 视频重命名与撤销预览按目录及其文件分组；FC2 文件夹正向预览只汇总跳过数量、长度截断数量、制作人更新数量与旧新制作人对应关系，默认仅逐项列出其他原因，确认菜单可按 `2` 展开全部待改目录；撤销预览仍逐项列出全部目录。三种原地修改工具选批撤销时只预览所选批次，完成后刷新列表。复制工具目标菜单首项为源目录旁，第二项为项目默认输出。
- 非视频复制工具选定目标后始终显示源、目标预览并等待确认，目标不存在时也不可直接开始写入。
- `site_state.py` 在当前 Python 进程内统计实际导航到 `/articles/...` 或 `/search` 的次数；第 50 次只提示一次，不限制导航，重新启动程序后从 0 计数。主页、演员页、缓存命中和相同 URL 的页面读取不计入。项目 `~outputs/fc2cmadb-site-state.sqlite3` 只保存 30 天有效的販売者当前名、旧名和 slug，不持久化访问计数。
- FC2 目录更新工具用 `PersistentBrowser.navigate()` 打开 `/search?keyword=...&stype=writer`，只接受当前名或旧名精确匹配的 `Writers/Show` 或完整 `Search/Writer` 列表中的唯一结果。扫描前统计販売者名称频率，先处理有效缓存，再优先搜索高频未缓存组；本批复用边界，跨批在 30 天内命中缓存即跳过站点搜索。目标名称保留原目录标题，过长时复用主程序截断规则。一次交互会话复用同一 Chrome，单独使用 `--undo` 参数入口不启动浏览器。搜索网址默认间隔 12 秒，可用 `--interval` 在 2–32 秒内调整。首次 429 即停止扫描，未处理目录计为跳过；此前已准备的计划仍预览并须用户确认才可改名。执行计划按目录深度排序，保证子目录先于父目录。
- FC2 目录更新预览只逐项展示其他原因；末尾按待改目录统计原因，长度截断和制作人更新可同时计入，其他原因仅计两者均不符合的目录。
- Python 与 PowerShell 预览均按共同子序列尽量缩短差异标色；长文本使用有界计算，PowerShell 不拆开 UTF-16 代理项对。
- `tests/`：不访问网络的 `unittest` 测试。
- 独立 Chrome profile：位于 `%LOCALAPPDATA%\fc2cmadb-crawler\chrome-profile`，仅保存本机浏览器登录状态，不属于项目文件或 Git。
- Chrome 调试端口就绪后先限时解析 ChromeDriver 路径，再以 30 秒本地连接超时附加 WebDriver；终端分别提示这两个阶段，方便定位启动停顿。
- `~archive/`：保留的旧版本和审计材料，不含真实 secret。
- `~outputs/`、`~temp/`：不进入 Git 的生成结果与临时内容。

## 开发流程

行为变更先添加离线测试，再修改实现。常用验证命令：

```powershell
python -m unittest discover -s tests -v
python -m compileall -q fc2cmadb_crawler tools tests
```

`tests/test_persistent_browser_profile.py` 覆盖普通 Chrome 独立启动后附加、当前登录页复用、统一 CDP 导航、同 URL 跳过和退出只断开驱动；测试不启动真实 Chrome。

`tests/test_fc2_number_input.py` 覆盖数字键菜单、模式保持、FC2 详情 URL、唯一/多演员解析，以及登录准备早于业务输入。

`tests/test_shortcut_urls.py` 覆盖原有 `id_{演员ID} - latest_{最新番号}` 快捷方式名称，以及作品目录不创建 `.url`。

真实站点抓取依赖本机 Chrome、用户手动登录的持久 profile 和目标站点可用性，不属于自动化验证。依赖变更更新 `requirements.txt`；公开行为或安装使用变化更新根目录 README；所有用户可见变更更新 `docs/CHANGELOG.md`。

## 项目评测集

下表中的真实样例来自既有项目需求和回归测试；预测样例根据外部站点与本机环境可能变化而设。每次相关功能交付时，按输入、过程和结果逐项记录执行证据；离线测试只能证明其覆盖的路径，真实站点抓取须另行实测。

| 来源 | 输入及前置状态 | 预期行为（过程） | 预期输出（结果） | 判定证据 |
|---|---|---|---|---|
| 真实：演员抓取需求 | 已登录，输入演员 ID，站点返回多页作品 | 通过 `PersistentBrowser.navigate()` 逐页读取；复用会话；按作品建目录 | 演员目录有唯一演员 `.url`，作品目录无 `.url`，作品数量一致才报成功 | 离线测试、目录清单；真实站点可用时记录实际抓取 |
| 真实：FC2 番号输入需求 | 已登录，输入纯数字番号 | 打开对应详情页，等待 hydration，从主作品数据或主内容解析唯一演员，再调用共同抓取流程 | 唯一演员时进入抓取；多演员或无演员时给出明确错误 | `tests/test_fc2_number_input.py` 与实际入口试运行 |
| 真实：撤销需求 | 存在一次已记录的原地修改批次 | 先预览所选批次，再由用户确认，按记录恢复 | 只恢复所选批次；历史状态准确更新 | `tests/test_multistep_undo.py` 与工具入口操作 |
| 预测：站点挑战或限流 | 页面出现挑战或 HTTP 429 | 保留可见浏览器会话；不绕过验证；限流后停止受影响批次 | 给出可理解状态，已准备的修改仍需预览确认 | 浏览器日志和实际操作记录；离线模拟只能验证分支 |
| 预测：无网络或 Chrome 不可用 | 启动入口时缺少运行条件 | 在显示业务菜单前完成环境检查并报错 | 不创建不完整输出，不要求用户执行不可用菜单项 | 入口小样本试运行及错误输出 |

## 降低验证与挑战的统一方法

经两个爬虫项目的真实站点调试，核心原则是复用可信的普通浏览器会话，而不是反复制造新会话。`PersistentBrowser` 用项目专用持久 Profile 启动普通可见 Chrome，再从本机调试端口附加 Selenium；重新运行时优先复用仍存活的调试端口、当前页面、Cookie 和登录状态。CLI 退出只停止驱动服务，不关闭 Chrome。

所有 fc2cmadb 业务页必须调用 `PersistentBrowser.navigate()`；调用方禁止直接执行 `driver.get()`、`refresh()` 或自行创建 WebDriver。该入口跳过相同 URL、限制连续导航速率、通过 CDP `Page.navigate` 跳转，并在超时时调用 `Page.stopLoading`。演员第一页、后续分页、FC2 详情和准备页都遵守同一路径，且每个演员任务前不得重复访问首页。

挑战判断同时检查标题和可见正文，不得仅凭原始 HTML 中的 `cf-chl-widget` 或嵌入式 Turnstile iframe 判断整页挑战。入口先等待自动跳转，仅超时后提示用户在可见 Chrome 内处理；人工确认后等待现有页面解除挑战，不刷新页面。首次运行、用户关闭 Chrome、系统重启、Cookie 过期或站点策略变化后仍可能出现验证；代码不得绕过 CAPTCHA 或安全屏障。

FC2 详情页的 Inertia `article` 初始数据可能没有演员字段，演员链接由前端 hydration 稍后渲染。解析前必须等待“页面错误状态或可解析的数字演员链接”，不能只等待 `document.readyState=complete`。

姐妹项目 `leak` 对每个目标站点使用独立 Profile，并在同一受控入口内允许已经验证的 SupJav 会话同步 Cookie/UA 读取静态 HTML；只有明确 403/503 才回退可见浏览器。这里的单站项目不需要静态 HTTP 分支，但仍遵守“持久会话、单一导航入口、少访问首页、不刷新挑战页、退出不关 Chrome”的通用规则。

## 已知问题

- Chrome、Cloudflare 和目标站点页面结构属于外部不稳定依赖；离线测试不能证明真实抓取仍可用。
