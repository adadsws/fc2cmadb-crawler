# FC2 PPV Data Crawler

这是一个用于抓取 FC2 PPV 数据库 (fc2ppvdb.com) 上的演员影片信息的 Python 脚本。它会自动整理影片信息、创建文件夹数据库、并生成演员在该网站上的快捷方式。

## 1. 注意

请不要滥用本脚本。
如果本项目侵犯了版权，请联系我删除。

## 2. 功能

- 自动获取指定演员的所有影片信息（支持多页翻页）。
- 按 "fc2-ppv-{ID} {制作商}-{影片名}" 格式创建子文件夹。
- 创建直接跳转到 fc2ppvdb 页面的 Internet 快捷方式 (`.url`)。


## 3. 安装步骤

1.  确保已安装 **Chrome** 浏览器。

2.  克隆或下载本项目。
    ```bash
    git clone https://github.com/adadsws/fc2ppvdb-crawler.git
    cd fc2-ppv-crawler
    ```
3.  安装 Python 3.x 及依赖库:
    ```bash
    pip install -r requirements.txt
    ```

## 4. 使用步骤

1.  **准备 Cookies：**

    推荐使用浏览器插件导出 Cookies，包含 `age_pass`、`remember_web_*`、`cf_clearance` 等。

    - 安装 Chrome/Edge 插件：
      https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

    - 登录 fc2ppvdb.com 并通过人机验证。

    - 使用插件导出 Cookies，保存为 `fc2ppvdb.com_cookies.txt`，放置在脚本根目录。

2.  **配置目标演员：**

    打开 `main.py`，修改 `actresses_id` 变量：
    ```python
    actresses_id = 6061  # 替换为你想抓取的演员 ID
    ```
    演员 ID 即 fc2ppvdb.com/actresses/{id} URL 中的数字。

3.  **运行脚本：**
    ```bash
    python main.py
    ```

## 5. 目录结构说明

```
upload_v0.3/
├── main.py                         # 主程序
├── requirements.txt                # 依赖列表
├── CHANGELOG.md                    # 修改日志
├── fc2ppvdb.com_cookies.txt        # 身份验证 Cookie（自行导出）
├── recommend/
│   ├── 製作者_推荐_2026-01-08.json # 推荐制作者列表
│   └── torrent_source.json         # 种子来源推荐
└── {演员名}/                       # 输出文件夹
    ├── fc2-ppv-{ID} {制作商}-{片名}/
    └── id_{actressId} - latest_{filmId}.url
```
