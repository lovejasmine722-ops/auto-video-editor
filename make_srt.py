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
    print("📝 生成中英双语字幕...")
    zh = model.transcribe(str(video), language="zh", fp16=False,
        initial_prompt="以下是普通话口播视频内容：")
    en = model.transcribe(str(video), language="zh", fp16=False,
        task="translate")

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(zh["segments"], 1):
            # 找对应英文段
            en_text = ""
            for es in en["segments"]:
                if abs(es["start"] - seg["start"]) < 1.0:
                    en_text = es["text"].strip()
                    break
            zh_text = seg["text"].strip()
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n")
            f.write(f"{zh_text}\n")
            if en_text:
                f.write(f"{en_text}\n")
            f.write("\n")
    print("✅ 中英双语字幕完成")

elif mode == "en":
    result = model.transcribe(str(video), language="zh", fp16=False, task="translate")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text'].strip()}\n\n")
    print("✅ 英文字幕完成")

else:
    result = model.transcribe(str(video), language="zh", fp16=False,
        initial_prompt="以下是普通话口播视频内容：")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"], 1):
            f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text'].strip()}\n\n")
    print("✅ 中文字幕完成")
