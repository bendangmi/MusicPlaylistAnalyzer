# 网易云歌单分析系统

## 项目简介
网易云歌单分析系统是一个用于抓取、分析和可视化网易云音乐歌单信息的工具。它可以帮助用户深入了解歌单内容，包括歌曲列表、创作者信息、播放量统计以及封面拼贴等。

## 功能特性
- **歌单数据抓取**：从网易云音乐获取完整的歌单信息，包括歌曲名称、艺术家、专辑及播放统计数据。
- **多格式输出**：支持生成文本（TXT）、Markdown（MD）和图像格式的信息展示。
- **封面拼贴**：自动下载并拼接歌单中每首歌曲的封面，形成一个视觉化的封面墙。
- **智能分析**：通过调用DeepSeek API对歌单风格、封面设计趋势进行智能点评。
- **Web界面**：提供简单的Web界面供用户输入歌单ID和Cookie，并展示分析结果。

## 安装与依赖
### 依赖库
- `Flask` - Web框架
- `requests` - HTTP请求处理
- `Pillow` - 图像处理
- `deepseek` - 智能分析API

### 安装命令
```bash
pip install flask requests Pillow deepseek
```

## 使用指南
### 运行方式
1. 确保已安装所有依赖库。
2. 获取[DeepSeek API Key](https://platform.deepseek.com/) 并替换在代码中的`DEEPSEEK_API_KEY`。
3. 执行以下命令启动应用：
```bash
python web_music_search.py
```
4. 打开浏览器访问 `http://localhost:5000/` 输入歌单ID和有效的Cookie开始分析。

### 参数说明
- **playlist_id**: 需要分析的网易云歌单ID。
- **cookie**: 用户的网易云Cookie，确保有权限访问该歌单。

## 注意事项
- 请勿滥用本工具，请遵守网易云音乐的[服务条款](https://music.163.com/#/about)。
- Cookie应为有效且属于本人账号，不得使用他人账户。
- 不建议公开分享生成的分析结果，以免泄露个人信息。

## 目录结构
```
├── templates/
│   └── index.html          # Web前端模板
├── music_serach.py         # 命令行版本主程序
├── playlist_info.md        # Markdown格式示例输出
├── readme.md               # 当前文档
└── web_music_search.py     # Web版主程序
```

## 开源许可
本项目采用MIT License发布。