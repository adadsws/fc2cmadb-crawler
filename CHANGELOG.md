# Changelog

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
