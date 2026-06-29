# FC2 PPV Data Crawler

这是一个用于抓取 FC2 PPV 数据库 (fc2cmadb.com) 上的演员影片信息的 Python 脚本。它会自动整理影片信息、创建文件夹数据库、并生成演员在该网站上的快捷方式。

## 1. 注意

请不要滥用本脚本。
如果本项目侵犯了版权，请联系我删除。

## 2. 功能

- 自动获取指定演员的所有影片信息（支持多页翻页）。
- 按 "fc2-ppv-{ID} {制作商}-{影片名}" 格式创建子文件夹。
- 影片子文件夹名称最多保留 80 个字符，过长时以 `+++` 标记截断。
- 自动检测本机 Chrome 主版本，减少 ChromeDriver 版本不匹配问题。
- 演员文件夹名称只使用演员主名称，不包含别名。
- 抓取结束后校验影片数量，只有提取数量与网页显示总数一致才提示成功。
- 创建直接跳转到 fc2cmadb 页面的 Internet 快捷方式 (`.url`)。
- 附带非媒体文件复制工具：可排除视频、图片，统计剩余文件大小，确认后按原目录结构复制。


## 3. 安装步骤

1.  确保已安装 **Chrome** 浏览器。
    脚本会自动检测 Chrome 主版本。如遇到 ChromeDriver 版本不匹配，也可以手动指定：
    ```powershell
    $env:CHROME_VERSION_MAIN="148"
    python main.py
    ```

2.  克隆或下载本项目。
    ```bash
    git clone https://github.com/adadsws/fc2ppvdb-crawler.git
    cd fc2ppvdb-crawler
    ```
3.  安装 Python 3.x 及依赖库:
    ```bash
    pip install -r requirements.txt
    ```

## 4. 使用步骤

1.  **准备 Cookies：**

    推荐使用浏览器插件导出 Cookies，包含 `ageVerified`、`remember_web_*`、`fc2cmadb_session` 等。
    脚本会自动跳过导出文件中的 `cf_clearance`，该 Cookie 与浏览器会话指纹绑定，不建议从文件加载。

    - 安装 Chrome/Edge 插件：
      https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

    - 登录 fc2cmadb.com，并在浏览器中完成站点要求的确认。

    - 使用插件导出 Cookies，保存为 `fc2cmadb.com_cookies.txt`，放置在脚本根目录。

2.  **配置目标演员：**

    打开 `main.py`，修改 `actresses_id` 变量：
    ```python
    actresses_id = 6061  # 替换为你想抓取的演员 ID
    ```
    演员 ID 即 fc2cmadb.com/actresses/{id} URL 中的数字。

3.  **运行脚本：**
    ```bash
    python main.py
    ```

    Windows 下也可以直接双击 `run_fc2cmadb_crawler.bat` 启动。
    启动后 CMD 会提示输入数字：`1` 使用 `main.py` 中的默认 `actresses_id`，`2` 手动输入新的演员 ID。

## 5. 非媒体文件复制工具

如需从一个目录中复制除视频、图片以外的所有文件，可运行：

```bash
python copy_non_media_files.py
```

Windows 下也可以直接双击 `run_copy_non_media_files.bat` 启动。

脚本会先提示输入源路径并扫描，显示将复制的文件数量和总大小。之后使用数字选择操作：

```text
1. 复制到默认目标路径
2. 手动输入目标路径后复制
0. 取消
```

默认目标路径为源目录同级的 `{源目录名}_non_media_files`。复制时会保留所有子文件夹结构。若目标路径已存在，会再次使用数字选择是否继续覆盖同名文件。

正式复制时会显示进度条，包含百分比、已复制大小、总大小和已完成文件数。

也可以直接传入参数：

```bash
python copy_non_media_files.py "D:\source_folder" "D:\target_folder"
```

传入目标路径参数时，菜单中的 `1` 会变为复制到指定目标路径。

## 6. 目录结构说明

```
fc2ppvdb-crawler/
├── main.py                         # 主程序
├── copy_non_media_files.py         # 复制非视频/非图片文件工具
├── requirements.txt                # 依赖列表
├── CHANGELOG.md                    # 修改日志
├── run_fc2cmadb_crawler.bat         # Windows 启动脚本
├── run_copy_non_media_files.bat     # Windows 非媒体复制工具启动脚本
├── fc2cmadb.com_cookies.txt         # 身份验证 Cookie（自行导出，已忽略）
├── recommend/
│   ├── 製作者_推荐_2026-01-08.json # 推荐制作者列表
│   └── torrent_source.json         # 种子来源推荐
└── output/                         # 输出文件夹（已忽略）
    └── {演员名}/
        ├── fc2-ppv-{ID} {制作商}-{片名}/ # 过长时以 +++ 截断
        └── id_{actressId} - latest_{filmId}.url
```
