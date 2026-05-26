import whisper, sys
from pathlib import Path

mode = sys.argv[1] if len(sys.argv) > 1 else "zh"
model = whisper.load_model("medium")

video = Path.home() / "video-pipeline/output/merged_temp.mp4"
srt_path = Path.home() / "video-pipeline/output/subtitles.srt"

def fmt(s):
    h,m = divmod(int(s),3600); m,sc = divmod(m,60)
    ms = int((s-int(s))*1000)
    return f"{h:02}:{m:02}:{sc:02},{ms:03}"

if mode == "zh+en":
    # 中文转录
    zh = model.transcribe(str(video), language="zh", fp16=False,
        initial_prompt="以下是普通话口播视频内容：")
    # 英文翻译
    en = model.transcribe(str(video), language="zh", fp16=False,
        task="translate")
    
    with open(srt_path, "w") as f:
        for i, (zs, es) in enumerate(zip(zh["segments"], en["segments"]), 1):
            f.write(f"{i}\n{fmt(zs['start'])} --> {fmt(zs['end'])}\n")
            f.write(f"{zs['text'].strip()}\n{es['text'].strip()}\n\n")
    print(f"✅ 中英双语字幕生成完成")

elif mode == "en":
    result = model.transcribe(str(video), language="zh", fp16=False, task="translate")
    with open(srt_path, "w") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text'].strip()}\n\n")
    print(f"✅ 英文字幕生成完成")

else:
    result = model.transcribe(str(video), language="zh", fp16=False,
        initial_prompt="以下是普通话口播视频内容：")
    with open(srt_path, "w") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text'].strip()}\n\n")
    print(f"✅ 中文字幕生成完成")
