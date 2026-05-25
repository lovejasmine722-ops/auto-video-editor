#!/bin/bash
# =====================================
# 流水线二：对标视频复刻完整流程
# =====================================

VIDEOLINGO=~/VideoLingo
OUTPUT=~/video-pipeline/output
STABLE=~/video-pipeline-STABLE

echo "======================================="
echo "🎬 流水线二：对标视频复刻"
echo "======================================="

# ① 输入对标视频
echo ""
echo "📎 支持平台：YouTube / TikTok / Instagram / 小红书"
echo "   抖音请先用 f2 下载后输入本地路径"
echo ""
# 列出 reference 文件夹里的视频
REF_DIR=~/video-pipeline/reference
echo ""
echo "📂 reference 文件夹里的视频："
ls -1 $REF_DIR/*.mp4 $REF_DIR/*.MP4 2>/dev/null | nl -w2 -s") "
echo ""
echo "输入数字选择本地视频，或直接输入 URL"
read -p "选择或输入: " VIDEO_CHOICE

# 判断是数字还是URL
if [[ "$VIDEO_CHOICE" =~ ^[0-9]+$ ]]; then
  VIDEO_INPUT=$(ls -1 $REF_DIR/*.mp4 $REF_DIR/*.MP4 2>/dev/null | sed -n "${VIDEO_CHOICE}p")
  echo "✅ 已选择: $(basename $VIDEO_INPUT)"
else
  VIDEO_INPUT=$VIDEO_CHOICE
fi

# ② 选择目标语言
echo ""
echo "🌐 选择输出语言："
echo "   1) 中文（保持原语言）"
echo "   2) 英文（翻译成英文）"
echo "   3) 中英双语字幕"
read -p "选择 [1-3，默认1]: " LANG_NUM
case $LANG_NUM in
  2) LANG="en" ;;
  3) LANG="zh+en" ;;
  *) LANG="zh" ;;
esac

# ③ 品牌名替换
echo ""
echo "🏷️  品牌名替换（将对标视频中的竞品名替换为你的品牌）"
read -p "竞品名称（例如：透蜜，留空跳过）: " OLD_BRAND
read -p "你的品牌名（例如：醒肌密）: " NEW_BRAND

# ④ 选择配音风格
echo ""
echo "🎙️  选择配音声音："
echo "   1) 中文活泼女声（带货推荐）"
echo "   2) 中文年轻男声"
echo "   3) 英文活泼女声（TikTok推荐）"
echo "   4) 英文男声"
read -p "选择 [1-4，默认1]: " VOICE_NUM
case $VOICE_NUM in
  2) VOICE="zh-CN-YunxiNeural" ;;
  3) VOICE="en-US-JennyNeural" ;;
  4) VOICE="en-US-GuyNeural" ;;
  *) VOICE="zh-CN-XiaoxiaoNeural" ;;
esac

# ⑤ 选择字幕风格
echo ""
echo "🎨 选择字幕风格："
echo "   1) 白色字幕 + 黑色描边"
echo "   2) 关键词黄色高亮（推荐）"
echo "   3) 淡入淡出"
echo "   4) 卡拉OK"
read -p "选择 [1-4，默认2]: " STYLE_NUM
case $STYLE_NUM in
  1) STYLE="normal" ;;
  3) STYLE="fade" ;;
  4) STYLE="karaoke" ;;
  *) STYLE="highlight" ;;
esac

if [ "$STYLE" = "highlight" ]; then
  echo ""
  read -p "🔑 关键词（空格分隔，回车跳过）: " KEYWORDS
fi

echo ""
echo "======================================="
echo "📋 确认配置："
echo "   视频: $VIDEO_INPUT"
echo "   语言: $LANG"
echo "   品牌替换: $OLD_BRAND → $NEW_BRAND"
echo "   配音: $VOICE"
echo "   字幕: $STYLE"
echo "======================================="
read -p "确认开始？(y/n): " CONFIRM
[ "$CONFIRM" != "y" ] && exit 0

mkdir -p $OUTPUT

# STEP 1: 下载视频
echo ""
echo "📥 STEP 1: 下载视频..."
if [[ "$VIDEO_INPUT" == http* ]]; then
  if [[ "$VIDEO_INPUT" == *douyin* ]] || [[ "$VIDEO_INPUT" == *v.douyin* ]]; then
    f2 douyin -c ~/.f2_douyin.yaml -M one \
      -u "$VIDEO_INPUT" \
      -p ~/video-pipeline/reference/
  else
    yt-dlp -o "$OUTPUT/reference.%(ext)s" \
      --merge-output-format mp4 "$VIDEO_INPUT"
    mv $OUTPUT/reference.mp4 ~/video-pipeline/reference/reference.mp4 2>/dev/null
  fi
else
  cp "$VIDEO_INPUT" ~/video-pipeline/reference/reference.mp4
fi
echo "✅ 下载完成"

# STEP 2: VideoLingo 提取+翻译+字幕
echo ""
echo "📝 STEP 2: VideoLingo 处理（提取文案+字幕）..."
cd $VIDEOLINGO
source .venv/bin/activate

REF_VIDEO=$(ls ~/video-pipeline/reference/*.mp4 | tail -1)
python3 << PYEOF
import subprocess, shutil
from pathlib import Path

ref = "$REF_VIDEO"
out_dir = Path("$OUTPUT/videolingo")
out_dir.mkdir(exist_ok=True)
shutil.copy(ref, out_dir / "input.mp4")
print(f"✅ 视频已准备: {out_dir}/input.mp4")
print("请在 VideoLingo 界面处理后继续")
PYEOF

echo "⏸️  请在 VideoLingo 界面完成字幕提取，完成后按回车继续..."
open http://localhost:8501
read -p "VideoLingo 处理完成后按回车继续: "

# STEP 3: 提取文案并替换品牌名
echo ""
echo "✍️  STEP 3: 提取文案并替换品牌名..."
python3 << PYEOF
from pathlib import Path
import json, re

# 从 VideoLingo 输出找字幕文件
vl_dir = Path.home() / "VideoLingo"
srt_files = list(vl_dir.rglob("*.srt")) + list(Path("$OUTPUT/videolingo").rglob("*.srt"))

if srt_files:
    srt = open(srt_files[-1]).read()
    text = re.sub(r'\d+\n[\d:,]+ --> [\d:,]+\n', '', srt).strip()
    
    # 品牌名替换
    if "$OLD_BRAND" and "$NEW_BRAND":
        text = text.replace("$OLD_BRAND", "$NEW_BRAND")
        print(f"✅ 品牌名替换: $OLD_BRAND → $NEW_BRAND")
    
    open("$OUTPUT/new_script.txt", "w").write(text)
    print(f"✅ 文案提取完成")
    print(f"预览: {text[:100]}...")
else:
    print("⚠️  未找到字幕文件，用 Whisper 重新提取")
    import whisper
    model = whisper.load_model("medium")
    result = model.transcribe("$REF_VIDEO", language="zh", fp16=False)
    text = result["text"]
    if "$OLD_BRAND" and "$NEW_BRAND":
        text = text.replace("$OLD_BRAND", "$NEW_BRAND")
    open("$OUTPUT/new_script.txt", "w").write(text)
    print(f"✅ 文案提取完成: {text[:100]}...")
PYEOF

# 人工确认文案
echo ""
cat $OUTPUT/new_script.txt
echo ""
read -p "文案是否满意？y继续 / e编辑: " CHECK
if [ "$CHECK" = "e" ]; then
  open $OUTPUT/new_script.txt
  read -p "编辑完成后按回车继续: "
fi

# STEP 4: 清理文案+TTS配音
echo ""
echo "🎙️  STEP 4: 合成配音..."
python3 << PYEOF
import re
from pathlib import Path

text = open("$OUTPUT/new_script.txt").read()
text = re.sub(r'\*+', '', text)
text = re.sub(r'【.*?】', '', text)
text = re.sub(r'（[^）]*?）', '', text)
text = re.sub(r'\n+', '，', text)
text = re.sub(r'，+', '，', text).strip()
open("$OUTPUT/clean_script.txt", "w").write(text)
print(f"✅ 文案清理完成: {text[:100]}...")
PYEOF

edge-tts \
  --voice "$VOICE" \
  --rate="+15%" --pitch="+5Hz" \
  --text "$(cat $OUTPUT/clean_script.txt)" \
  --write-media $OUTPUT/new_voice.mp3
echo "✅ 配音完成"

# STEP 5: 合成视频
echo ""
echo "🎞️  STEP 5: 合成视频..."
REF_VIDEO=$(ls ~/video-pipeline/reference/*.mp4 | tail -1)
AUDIO_DUR=$(ffprobe -v quiet -show_entries format=duration -of csv=p=0 $OUTPUT/new_voice.mp3)

/usr/local/bin/ffmpeg-full \
  -stream_loop -1 -i "$REF_VIDEO" \
  -i $OUTPUT/new_voice.mp3 \
  -map 0:v -map 1:a \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -shortest \
  $OUTPUT/merged_temp.mp4 -y 2>/dev/null
echo "✅ 视频合成完成"

# STEP 6: 字幕
echo ""
echo "📝 STEP 6: 生成字幕..."
python3 $STABLE/make_srt.py
python3 $STABLE/make_subtitle.py "$STYLE" "$KEYWORDS"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FINAL=$OUTPUT/final_remake_${TIMESTAMP}.mp4

/usr/local/bin/ffmpeg-full \
  -i $OUTPUT/merged_temp.mp4 \
  -vf "ass=/Users/mac/video-pipeline/output/subtitles.ass" \
  -c:v libx264 -preset fast -crf 23 -c:a copy \
  $FINAL -y 2>/dev/null

# STEP 7: 确认发布
echo ""
echo "======================================="
echo "🎉 视频制作完成！"
echo "   输出: $FINAL"
echo "======================================="
open $OUTPUT

read -p "是否立即发布？(y/n): " PUBLISH
if [ "$PUBLISH" = "y" ]; then
  echo ""
  echo "📢 选择发布平台："
  echo "   1) 抖音  2) 小红书  3) 视频号  4) 快手"
  read -p "输入数字（空格分隔）: " PLATFORMS
  read -p "标题: " TITLE
  read -p "标签（空格分隔）: " TAGS
  read -p "原创声明？(y/n，默认y): " ORIGINAL
  [ "$ORIGINAL" != "n" ] && IS_ORIGINAL="true" || IS_ORIGINAL="false"

  echo ""
  echo "📋 发布确认："
  echo "   标题: $TITLE | 平台: $PLATFORMS | 原创: $IS_ORIGINAL"
  read -p "确认发布？(y/n): " FINAL_CONFIRM
  if [ "$FINAL_CONFIRM" = "y" ]; then
    open http://localhost:8080
    echo "✅ 请在 AiToEarn 界面完成发布"
  fi
fi
