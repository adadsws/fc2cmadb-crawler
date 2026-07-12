# FC2 PPV Data Crawler

用于抓取 `fc2cmadb.com` 演员影片信息，并按作品自动创建文件夹和 `.url` 快捷方式。

请不要滥用本脚本。如本项目侵犯版权，请联系删除。

## 功能

- 抓取指定演员的所有影片，支持分页。
- 按 `fc2-ppv-{ID} {制作商}-{影片名}` 创建文件夹。
- 文件夹名过长时自动截断并以 `+++` 标记。
- 自动检测 Chrome 主版本。
- 抓取结束后校验影片数量，数量一致才提示成功。
- 附带非媒体文件复制工具和快捷方式域名修复工具。

## 安装

需要 Python 3.x 和 Chrome。

```bash
git clone https://github.com/adadsws/fc2ppvdb-crawler.git
cd fc2ppvdb-crawler
pip install -r requirements.txt
```

## Cookie

登录 `fc2cmadb.com` 后，用浏览器插件导出 Cookie：

https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc

保存为：

```text
fc2cmadb.com_cookies.txt
```

放在项目根目录。脚本会跳过 `cf_clearance`，保留浏览器自己的会话验证。

## 运行爬虫

默认演员 ID 在 `fc2cmadb_crawler/config.py`：

```python
DEFAULT_ACTRESS_ID = 6061
```

启动：

```bash
python main.py
```

Windows 可双击：

```text
run_fc2cmadb_crawler.bat
```

启动后直接输入演员 ID；直接回车使用配置文件默认 ID。完成一个演员后会回到输入提示，可继续输入下一个演员 ID，输入 `q` 退出。

如需手动指定 Chrome 主版本：

```powershell
$env:CHROME_VERSION_MAIN="148"
python main.py
```

## 工具

复制除视频、图片外的文件，保留目录结构：

```bash
python -m fc2cmadb_crawler.copy_non_media_files
python -m fc2cmadb_crawler.copy_non_media_files "D:\source_folder" "D:\target_folder"
```

Windows 可双击 `run_copy_non_media_files.bat`。

批量把 `.url` 中域名包含 `fc2` 的链接改为 `fc2cmadb.com`：

```bash
python -m fc2cmadb_crawler.update_shortcut_domains
python -m fc2cmadb_crawler.update_shortcut_domains "D:\shortcut_folder"
```

Windows 可双击 `run_update_shortcut_domains.bat`。

## 目录结构

```text
fc2ppvdb-crawler/
├── main.py
├── fc2cmadb_crawler/
│   ├── config.py
│   ├── crawler.py
│   ├── copy_non_media_files.py
│   ├── copy_non_media.py
│   ├── update_shortcut_domains.py
│   └── shortcut_domains.py
├── run_fc2cmadb_crawler.bat
├── run_copy_non_media_files.bat
├── run_update_shortcut_domains.bat
├── requirements.txt
├── CHANGELOG.md
├── recommend_20260629/
└── output/
```
