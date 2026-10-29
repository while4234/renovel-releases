# 两分钟介绍视频

使用已脱敏的安卓模拟器截图，以及 Windows 改写左右对照截图，配中文文字和原创 96 BPM 纯音乐，无人声、无第三方录音采样。画面不伪造软件操作结果。

`timeline.json` 保存完整中文文案、时长与截图对应关系；`scripts/render-intro.py` 生成背景、手机画面动画、原创配乐及最终视频，并验证分辨率、帧率、时长和体积。

```powershell
python scripts/render-intro.py --screenshots docs/images --output artifacts/private/promo
```

需要 Pillow、numpy、FFmpeg 和中文字体。输出为 1920×1080、30 帧、120 秒的 H.264/AAC MP4，附封面和验证记录。中间文件保存在忽略目录；正式视频作为 GitHub、Gitee 发行版附件提供。脚本和原创配乐编排随项目采用 MIT 许可，第三方字体按本机字体许可使用。
