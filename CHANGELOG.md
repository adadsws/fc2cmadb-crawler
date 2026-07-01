# Changelog

## 2026-07-01

### 爬虫 / Crawler

- **调试 ID 4808 访问异常**：确认 `https://fc2cmadb.com/actresses/4808` 以及对应最新作品页返回 404，属于目标页面不存在、删除或新站 ID 变化，不是 Cookie 或启动参数错误。
- **补充指定演员 ID 调试记录**：围绕 `id=4221`、`id=4808` 调试时暴露的错误页或无卡片加载场景，补强页面状态识别、错误 URL 输出和终止提示。
- **增强错误页诊断**：Inertia Error 页面会输出错误状态、错误 URL 和页面标题；遇到 404 时提示检查演员 ID 是否仍有效，遇到 403 且未登录时提示导出 `fc2cmadb.com_cookies.txt`。
- **启动时选择演员 ID**：CMD 中可用数字选择配置文件默认 ID，或手动输入新的演员 ID。
- **严格数量校验**：抓取完成后会校验提取数量是否等于网页显示总数，例如 `表示中： 1 から 30 件目、全： 212 件`；数量不一致时停止创建文件夹。

### 项目结构 / Structure

- **主入口精简**：根目录 [main.py](main.py) 只保留启动入口。
- **代码集中入包**：爬虫和工具脚本实现移动到 `fc2cmadb_crawler/`。
- **统一参数文件**：主程序参数和工具脚本参数统一放入 `fc2cmadb_crawler/config.py`。
- **工具入口入包**：非媒体复制和快捷方式域名修复入口移动到 `fc2cmadb_crawler/`，通过 `python -m fc2cmadb_crawler.copy_non_media_files` 和 `python -m fc2cmadb_crawler.update_shortcut_domains` 启动。
- **批处理同步**：`run_copy_non_media_files.bat`、`run_update_shortcut_domains.bat` 改为模块方式启动工具。
- **根目录收敛**：根目录 Python 文件只保留 `main.py`。

### 工具 / Utilities

- **新增非媒体文件复制工具**：可输入源路径，排除视频和图片文件，先统计将复制的文件数量与总大小，确认后复制。
- **复制工具数字菜单**：复制前可输入 `1` 使用默认/指定目标路径、`2` 手动输入目标路径、`0` 取消；目标路径存在时也用数字确认。
- **复制工具进度条**：复制阶段显示百分比、已复制大小、总大小和文件数进度，并保留原文件夹结构。
- **新增快捷方式域名修复工具**：递归扫描 `.url` 文件，只处理 `URL=` 中域名包含 `fc2` 的链接，把域名改为 `fc2cmadb.com` 并保留路径、查询参数和片段。
- **快捷方式修复前统计**：修改前先统计并显示各链接域名出现次数，再显示待修改数量和预览，用户确认后才写入。

### 数据快照 / Snapshot Data

- **提交推荐快照当前状态**：`recommend_20260629/` 的修改、删除、重命名和新增文件已全部提交。
- **推荐快照不忽略**：`.gitignore` 明确取消忽略 `recommend_20260629/` 及其子文件，保证该目录完整纳入版本管理。
- **推荐快照路径整理**：过长的推荐快照目录名改为截断后的 `+++` 形式，避免路径过长影响后续操作。

### 文档 / Documentation

- **README 同步更新**：补充新站使用方式、Cookie 文件名、工具启动命令、项目结构、数量校验和工具说明。
- **CHANGELOG 补全历史**：本文件补记此前所有主要变更，覆盖爬虫、工具、结构、数据快照和维护规则。
- **新增文档更新规则**：本地 `AGENTS.md` 记录每次变更需要检查并同步哪些文档，包括 `CHANGELOG.md`、`README.md`、`requirements.txt`、`.gitignore` 和 `run_*.bat`。

### 维护 / Maintenance

- **AGENTS.md 本地化**：`AGENTS.md` 改为本地忽略文件，不再提交或推送到 GitHub；本地文件保留用于记录协作规则。
- **忽略规则更新**：`.gitignore` 增加 `AGENTS.md`，并继续忽略 Cookie、输出目录、缓存和本地归档数据。
- **分组提交约定落地**：代码整理和 `recommend_20260629/` 快照更新分别提交，避免混合 Codex 修改和用户数据快照。

## 2026-06-29

### 破坏性修复 / Breaking Fixes

- **切换到新站域名**：默认站点从 `fc2ppvdb.com` 更新为 `fc2cmadb.com`。
- **适配新版 UI**：改为优先解析 Inertia JSON，并在 deferred 数据渲染后从作品卡片 DOM 回退提取 `video_id`、标题和販売者。
- **更新 Cookie 文件名**：新站登录态默认读取 `fc2cmadb.com_cookies.txt`，并继续跳过 `cf_clearance`。

### 修复 / Fixes

- **修复脚本启动目录问题**：Cookie 会同时从当前目录和脚本目录查找，避免从项目根目录启动时报找不到 Cookie。
- **修复作品卡片双链接解析**：新版卡片同时包含封面链接和标题链接，现按卡片逐个解析，优先读取标题链接，避免标题退化成番号、販売者变成 `UNKNOWN`。
- **修复控制台编码报错**：Windows GBK 控制台遇到特殊字符时不再触发 `UnicodeEncodeError` 并跳过影片。
- **修复总数和页数识别**：支持 `表示中： 1 から 30 件目、全： 212 件` 这种新站文案，并按总数计算总页数。
- **增强 404 调试提示**：演员页或作品页返回 404 时会输出错误 URL、页面标题，并提示页面可能不存在、已删除或新站 ID 已变化。

### 功能改进 / Improvements

- **启动时选择演员 ID**：CMD 中可选择使用配置文件默认演员 ID，或手动输入新的演员 ID。
- **严格数量校验**：抓取完成后只有提取数量与网页显示总数一致才提示成功；不一致时停止创建文件夹并返回错误。
- **输出目录固定**：生成的演员文件夹统一写入 `output/`，避免污染项目根目录。
- **新增 Windows 启动脚本**：可直接双击 `run_fc2cmadb_crawler.bat` 启动。
- **整理项目结构**：发布文件移动到项目根目录，去掉带版本号的发布目录；旧实验和运行数据归档到 `~archived/` 并通过 `.gitignore` 排除。
- **入口与逻辑分离**：`main.py` 仅保留启动入口，爬虫实现移动到 `fc2cmadb_crawler/crawler.py`。
- **集中参数配置**：主程序和工具脚本参数统一放入 `fc2cmadb_crawler/config.py`。

### 工具 / Utilities

- **新增非媒体文件复制工具**：`python -m fc2cmadb_crawler.copy_non_media_files` 可输入源路径和目标路径，排除视频、图片文件后统计剩余文件数量和大小，确认后按原文件夹结构复制。
- **优化复制工具交互顺序**：现在会先扫描并显示非媒体文件总大小，再通过数字菜单选择目标路径并复制。
- **复制工具改为数字菜单**：扫描后可输入 `1` 使用默认/指定目标路径复制、`2` 手动输入目标路径复制、`0` 取消；目标路径已存在时也用数字确认。
- **复制工具新增进度条**：复制阶段按已复制字节和文件数显示百分比、大小和进度。
- **新增非媒体复制启动脚本**：Windows 下可直接双击 `run_copy_non_media_files.bat` 启动工具。
- **新增快捷方式域名修复工具**：`python -m fc2cmadb_crawler.update_shortcut_domains` 可递归扫描 `.url` 快捷方式，预览后只将 `URL=` 中域名包含 `fc2` 的链接批量改为 `fc2cmadb.com`，并保留原路径和查询参数。
- **快捷方式修复工具新增域名统计**：正式修改前会先统计并显示 `.url` 中各链接域名的出现次数。
- **新增快捷方式修复启动脚本**：Windows 下可直接双击 `run_update_shortcut_domains.bat` 启动工具。
- **工具脚本入包**：非媒体复制和快捷方式域名修复入口也移动到 `fc2cmadb_crawler/`，根目录只保留 `main.py`。

## 2026-06-01

### 修复 / Fixes

- **修复 ChromeDriver 版本不匹配**：启动时自动检测本机 Chrome 主版本，并传给 `undetected_chromedriver`，避免出现 `ChromeDriver only supports Chrome version X` 的启动失败。
  - 如需手动指定版本，可设置环境变量 `CHROME_VERSION_MAIN`。

- **修复演员名称提取**：演员名称现在只读取名称容器的直接文本，忽略 `aliases` 子节点，避免把别名一起写入演员文件夹名称。
  - 例如：`千佳 <div id="aliases">...</div>` 只提取 `千佳`。

- **修复单个影片卡片异常导致中断**：提取影片数据时恢复逐卡片异常处理，某个卡片结构异常时会跳过并继续处理后续影片。

- **修复异常退出后 Chrome 残留**：主流程改为 `main()`，并在 `finally` 中关闭 WebDriver，降低浏览器进程残留概率。

### 功能改进 / Improvements

- **影片文件夹名称长度限制**：影片子文件夹名称最多保留 80 个字符，达到或超过长度限制时使用 `+++` 作为截断标记。
  - Windows 不保留文件夹名末尾的英文句点，因此截断标记由 `......` 改为 `+++`。

- **失败时更早退出**：目标页面未加载影片卡片、HTML 解析失败、演员名称提取失败时会明确输出错误并结束流程，避免继续创建错误目录。

## 2026-03-25

### 破坏性修复 / Breaking Fixes

- **切换爬虫引擎**：将 `selenium.webdriver.Chrome` 替换为 `undetected_chromedriver.Chrome`
  - 原因：fc2ppvdb.com 使用 Cloudflare 反爬，标准 ChromeDriver 被识别为机器人，导致 `actress-articles` AJAX 接口返回空响应体（HTTP 200 但 body 长度为 0）
  - `undetected-chromedriver` 自动修补 ChromeDriver 特征指纹，成功绕过检测

- **修复 Cookie 加载逻辑**：`load_cookies_from_netscape_file()` 新增两项过滤：
  1. 跳过已过期的 Cookie（`expiry < now`）——原先加载的 `XSRF-TOKEN` 和 `fc2ppvdb_session` 已过期 12 天，覆盖了浏览器的新 Session
  2. 跳过 `cf_clearance`——该 Cookie 绑定 TLS 指纹，从文件加载会使 Cloudflare 验证失败；改由 `uc.Chrome` 自动获取

- **修复伪造 User-Agent**：移除了 `options.add_argument("user-agent=Chrome/138...")`
  - 原因：手动设置的 UA 版本（Chrome/138）与浏览器真实发送的 `sec-ch-ua`（Chrome/146）不一致，被 Cloudflare 识别为 bot

### 功能改进 / Improvements

- **利用 Cookie 跳过年龄验证**：不再点击 ENTER 按钮，直接加载 Cookie 文件中的 `age_pass` Cookie，访问 `/cookie/setage` 后服务器自动放行

- **分页改为按总页数终止**：从第一页 HTML 提取 `全：N件` 总数，计算 `total_pages = ceil(N / 40)`，循环在到达最后一页后立即停止，不再等待第 N+1 页超时（例如：193 件 → 5 页，不再尝试第 6 页）

- **演员文件夹重名自动编号**：文件夹已存在时改用 `_1`、`_2`… 后缀，不再退出程序

- **提取结果核验**：循环结束后对比提取数量与网页显示总数，不一致时输出警告

- **窗口最大化**：启动时自动调用 `driver.maximize_window()`

### 调试过程记录 / Debug Journey

1. 等待策略：`lazyload-wrapper` → XPath film cards → `document.readyState` → `#actress-articles a[href*='/articles/']`（最终有效）
2. 排查发现页面为 Vue.js SSR + AJAX 架构：SSR 渲染 "Loading..." 占位，Vue 通过 AJAX 补充数据
3. 禁用 JS 验证：SSR 仅渲染纯 Loading 占位，无任何影片数据
4. CDP 网络监控：捕获 `actress-articles?actressid=6061&page=1` → HTTP 200 但 body 空
5. 尝试 `requests.Session` 直接调用 API → 同样空响应（TLS 指纹被拒）
6. 尝试 `driver.execute_async_script` 内部 fetch → 同样空响应
7. 比对请求头发现 UA 版本不一致（Chrome/138 vs sec-ch-ua v146）
8. 检查 Cookie 发现 XSRF-TOKEN 和 Session 已过期 12 天
9. 改用 `undetected-chromedriver` + 不加载 `cf_clearance` + 跳过伪造 UA → 成功获取完整影片数据
