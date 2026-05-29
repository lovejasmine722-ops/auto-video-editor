#!/bin/bash
FFMPEG=/usr/local/bin/ffmpeg-full
OUTPUT=~/video-pipeline/output
TRIMMED=$OUTPUT/trimmed3

echo "======================================="
echo "🎬 视频处理流水线启动"
echo "======================================="

# ① 选择风格
echo ""
echo "🎨 选择字幕风格："
echo "   1) 白色字幕 + 黑色描边"
echo "   2) 白色字幕 + 关键词黄色高亮（推荐）"
echo "   3) 淡入淡出动态效果"
echo "   4) 卡拉OK变色效果"
echo ""
read -p "输入数字 [1-4，默认2]: " STYLE_NUM
case $STYLE_NUM in
  1) STYLE="normal" ;;
  3) STYLE="fade" ;;
  4) STYLE="karaoke" ;;
  *) STYLE="highlight" ;;
esac
echo "✅ 已选择: $STYLE"

# 语言选择
echo ""
echo "🌐 选择字幕语言："
echo "   1) 中文"
echo "   2) 英文"
echo "   3) 中英双语"
echo ""
read -p "输入数字 [1-3，默认1]: " LANG_NUM
case $LANG_NUM in
  2) LANG="en" ;;
  3) LANG="zh+en" ;;
  *) LANG="zh" ;;
esac
echo "✅ 语言: $LANG"

# ② 关键词输入（highlight才问）
KEYWORDS=""
if [ "$STYLE" = "highlight" ]; then
  echo ""
  echo "🔑 输入本期视频重点关键词"
  echo "   多个词用空格或逗号分隔，例如：女性 情感 价值"
  echo "   直接回车跳过"
  echo ""
  read -p "关键词：" KEYWORDS
  echo "✅ 关键词: $KEYWORDS"
fi

echo ""
echo "风格=$STYLE 关键词=$KEYWORDS"
echo "继续处理..."

# STEP 1: 去气口
echo ""
echo "✂️  STEP 1: 去除气口..."
rm -rf $TRIMMED && mkdir -p $TRIMMED
python3 ~/video-pipeline-STABLE/remove_silence.py
echo "✅ 完成"

# STEP 2: 拼接
echo "🔗 STEP 2: 拼接合成..."
ls $TRIMMED/*_cut.mp4 | sort | sed "s/^/file '/;s/$/'/" > /tmp/list.txt
$FFMPEG -f concat -safe 0 -i /tmp/list.txt \
  -c:v libx264 -preset fast -crf 23 \
  -c:a aac -b:a 128k \
  -af 'adelay=500|500' \
  $OUTPUT/merged_temp.mp4 -y 2>/dev/null
echo "✅ 完成"

# STEP 3: Whisper 字幕
echo "📝 STEP 3: 生成字幕..."
python3 ~/video-pipeline-STABLE/make_srt.py $LANG
echo "✅ 完成"

# STEP 4: 字幕样式（传入已收集的 STYLE 和 KEYWORDS）
echo "🎨 STEP 4: 生成字幕样式 ($STYLE)..."
echo "   关键词传入: $KEYWORDS"
python3 ~/video-pipeline-STABLE/make_subtitle.py "$STYLE" "$KEYWORDS" "$LANG"

# STEP 5: 烧录
echo "🎞️  STEP 5: 烧录字幕..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
FINAL=$OUTPUT/final_${STYLE}_${TIMESTAMP}.mp4

if [ "$STYLE" = "normal" ]; then
  $FFMPEG -i $OUTPUT/merged_temp.mp4 \
    -vf "subtitles=/Users/mac/video-pipeline/output/subtitles.srt:fontsdir=/System/Library/Fonts:force_style='FontName=STHeiti Medium,FontSize=44,Alignment=2,MarginV=150,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2,WrapStyle=1'" \
    -c:v libx264 -preset fast -crf 23 -c:a copy \
    $FINAL -y 2>/dev/null
else
  $FFMPEG -i $OUTPUT/merged_temp.mp4 \
    -vf "ass=/Users/mac/video-pipeline/output/subtitles.ass" \
    -c:v libx264 -preset fast -crf 23 -c:a copy \
    $FINAL -y 2>/dev/null
fi

SIZE=$(ls -lh $FINAL 2>/dev/null | awk '{print $5}')
DURATION=$(/opt/homebrew/bin/ffprobe -v quiet -show_entries format=duration \
  -of csv=p=0 $FINAL 2>/dev/null | awk '{printf "%.0f", $1}')
MIN=$((DURATION/60)); SEC=$((DURATION%60))

echo ""
echo "======================================="
echo "🎉 完成！"
echo "   风格: $STYLE"
echo "   输出: $FINAL"
echo "   大小: $SIZE"
echo "   时长: ${MIN}分${SEC}秒"
echo "======================================="
open $OUTPUT
