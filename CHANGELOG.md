# Changelog

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

### 功能改进 / Improvements

- **启动时选择演员 ID**：CMD 中可选择使用 `main.py` 默认 `actresses_id`，或手动输入新的演员 ID。
- **严格数量校验**：抓取完成后只有提取数量与网页显示总数一致才提示成功；不一致时停止创建文件夹并返回错误。
- **输出目录固定**：生成的演员文件夹统一写入 `output/`，避免污染项目根目录。
- **新增 Windows 启动脚本**：可直接双击 `run_fc2cmadb_crawler.bat` 启动。
- **整理项目结构**：发布文件移动到项目根目录，去掉带版本号的发布目录；旧实验和运行数据归档到 `~archived/` 并通过 `.gitignore` 排除。

### 工具 / Utilities

- **新增非媒体文件复制工具**：`copy_non_media_files.py` 可输入源路径和目标路径，排除视频、图片文件后统计剩余文件数量和大小，确认后按原文件夹结构复制。
- **优化复制工具交互顺序**：现在会先扫描并显示非媒体文件总大小，再通过数字菜单选择目标路径并复制。
- **复制工具改为数字菜单**：扫描后可输入 `1` 使用默认/指定目标路径复制、`2` 手动输入目标路径复制、`0` 取消；目标路径已存在时也用数字确认。
- **复制工具新增进度条**：复制阶段按已复制字节和文件数显示百分比、大小和进度。
- **新增非媒体复制启动脚本**：Windows 下可直接双击 `run_copy_non_media_files.bat` 启动工具。

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
