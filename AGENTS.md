# 项目代理规则

- 自动化验证必须离线运行，不得在测试中访问 `fc2cmadb.com` 或启动真实 Chrome 会话。
- 爬虫和工具生成、复制的结果统一写入 `~outputs/`，不得提交该目录内容。
- 修改 Cookie 文件结构或查找顺序时，必须同步维护 `secrets/**/*.example` 与相应离线测试；任何输出都不得包含 Cookie 正文。
- `reference/grill-with-docs` 是固定提交的只读 submodule，不得在项目任务中直接修改其工作树。
