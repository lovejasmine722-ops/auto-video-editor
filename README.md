# Auto Video Editor 🎬

基于 ffmpeg + Whisper 的自动视频剪辑流水线，专为口播视频优化。

## 功能
- ✂️ 自动去除气口/停顿（>0.2秒）
- 🔗 多段素材智能拼接
- 📝 Whisper 自动生成字幕（中/英/双语）
- 🎨 4种字幕风格（普通/高亮/淡入/卡拉OK）
- 🔑 关键词黄色高亮

## 使用方法
```bash
bash go.sh
```

## 环境要求
- macOS (Apple Silicon)
- Python 3.11+
- ffmpeg-full
- whisper

## 安装依赖
```bash
brew install ffmpeg-full
pip install openai-whisper moviepy auto-editor
```
