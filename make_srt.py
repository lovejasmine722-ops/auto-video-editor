import whisper, sys
from pathlib import Path

# 接收语言参数
# python3 make_srt.py zh     → 纯中文字幕
# python3 make_srt.py en     → 纯英文字幕  
# python3 make_srt.py zh+en  → 中英双语字幕

mode = sys.argv[1] if len(sys.argv) > 1 else "zh"

model = whisper.load_model("medium")

if mode == "en":
    # 直接转录为英文
    result = model.transcribe(
        str(Path.home() / "video-pipeline/output/merged_temp.mp4"),
        language="zh", fp16=False,
        task="translate",  # ← 直接翻译成英文
        initial_prompt="The following is a Chinese video translated to English:"
    )
else:
    # 中文转录
    result = model.transcribe(
        str(Path.home() / "video-pipeline/output/merged_temp.mp4"),
        language="zh", fp16=False,
        initial_prompt="以下是普通话口播视频内容："
    )

srt_path = Path.home() / "video-pipeline/output/subtitles.srt"

def fmt(s):
    h,m = divmod(int(s),3600); m,sc = divmod(m,60)
    ms = int((s-int(s))*1000)
    return f"{h:02}:{m:02}:{sc:02},{ms:03}"

# 如果双语，提前翻译一次
if mode == "zh+en":
    en_result = model.transcribe(
        str(Path.home() / "video-pipeline/output/merged_temp.mp4"),
        language="zh", fp16=False, task="translate"
    )
    en_segs = en_result["segments"]

with open(srt_path, "w", encoding="utf-8") as f:
    for i, seg in enumerate(result["segments"], 1):
        zh_text = seg["text"].strip()
        if mode == "zh+en":
            # 找时间重叠最多的英文段
            best_en, best_overlap = "", 0
            for es in en_segs:
                overlap = min(seg["end"], es["end"]) - max(seg["start"], es["start"])
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_en = es["text"].strip()
            text = f"{zh_text}\n{best_en}"
        else:
            text = zh_text
        f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{text}\n\n")

print(f"✅ 字幕生成完成（模式: {mode}）")
