# FC2 PPV Data Crawler

这是一个用于抓取 FC2 PPV 数据库 (fc2ppvdb.com) 上的演员影片信息的 Python 脚本。它会自动整理影片信息、创建文件夹数据库、并生成演员在该网站上的快捷方式。

This is a Python script used to scrape actress video information from the FC2 PPV database (fc2ppvdb.com). It automatically organizes video information, creates a folder database, and generates shortcuts for the actress on the website.

## 1. 注意 / Note

该网站似乎面临崩溃，请不要滥用本脚本。

The website seems to be facing crashes, please do not abuse this script.

## 2. 功能 / Features

- 自动获取指定演员的所有影片信息。
- 按 "ID 制作商-影片名" 格式创建文件夹。
- 创建直接跳转到 fc2ppvdb 页面的 Internet 快捷方式 (`.url`)。
- 支持通过 `Netscape` 格式的 `cookies.txt` 文件进行身份验证。

###

- Automatically retrieves all video information for a specified actress.
- Creates folders in the format "ID Maker-VideoName".
- Creates Internet shortcuts (`.url`) that link directly to the fc2ppvdb page.
- Supports authentication via `Netscape` format `cookies.txt` file.

## 3. 安装步骤 / Installation

1.  脚本依赖 Firefox 进行网页抓取，请确保已安装 Firefox 浏览器。

    The script relies on Firefox for web scraping, please ensure Firefox browser is installed.

2.  克隆或下载本项目。

    Clone or download this project.
    ```bash
    git clone https://github.com/adadsws/fc2ppvdb-crawler.git
    cd fc2-ppv-crawler
    ```
3.  安装 Python 3.x 及依赖库:

    Install Python 3.x and dependent libraries:
    ```bash
    pip install -r requirements.txt
    ```

## 4. 使用步骤 / Usage

1.  **准备 Cookies / Prepare Cookies:**
    推荐使用插件导出 Cookies。

    It is recommended to use a plugin to export Cookies.
    - 安装 Chrome/Edge 插件。
    Install Chrome/Edge plugin.
    https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc
      
      
    - 登录 fc2ppvdb.com 并通过人机验证等。
      
      Log in to fc2ppvdb.com and pass the captcha, etc.
    - 使用插件导出 Cookies，保存为 `fc2ppvdb.com_cookies.txt`，并将文件放置在脚本根目录。
      
      Use the plugin to export Cookies, save as `fc2ppvdb.com_cookies.txt`, and place the file in the script root directory.

2.  **配置目标演员 / Configure Target Actress:**
    - 打开 `main.py`。
      
      Open `main.py`.
    - 修改 `actresses_id` 变量为你想要抓取的演员 ID:
      
      Modify the `actresses_id` variable to the actress ID you want to scrape:
      ```python
      actresses_id = 11126  # Replace with the actress ID you want to scrape
      ```

3.  **运行脚本 / Run Script:**
    ```bash
    python main.py
    ```

## 5. 目录结构说明 / Directory Structure

- `main.py`: 主程序脚本 / Main program script.
- `requirements.txt`: 依赖列表 / Dependency list.
- `fc2ppvdb.com_cookies.txt`: 身份验证 Cookies（需自行生成） / Authentication Cookies (need to be generated manually).
- `recommend/`: 推荐列表文件夹 / Recommendation list folder.
  - `製作者_推荐_2026-01-08.json`: 个人推荐的制作者 / Personal recommended producers.
  - `torrent_source.json`: 种子来源推荐 / Recommended torrent sources.
- `sample_output_りん/`: 示例输出文件夹 / Sample output folder.
- `.gitignore`: Git 忽略文件配置 / Git ignore configuration.

## 6. 更新计划 / Update Plan
- [x] 整理代码和文档 / Organize code and documentation
- [x] 去除不可用的下载头像功能 / Remove unusable avatar download function
- [ ] 附带种子的演员推荐列表 / Actress recommendation list with torrents