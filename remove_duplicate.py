"""
检测并去除重复片段
原理：Whisper 转录后，相似度>80% 的片段视为重复，保留最后一版
"""
import sys
from pathlib import Path

def similarity(a, b):
    """简单字符相似度"""
    a, b = set(a), set(b)
    return len(a&b) / max(len(a|b), 1)

def remove_duplicates(segments, threshold=0.7):
    kept = []
    for seg in segments:
        is_dup = False
        for prev in kept[-5:]:  # 只比较前5条
            if similarity(seg["text"], prev["text"]) > threshold:
                # 重复了，保留时长更短的（更精炼的版本）
                if (seg["end"]-seg["start"]) < (prev["end"]-prev["start"]):
                    kept.remove(prev)
                    kept.append(seg)
                is_dup = True
                break
        if not is_dup:
            kept.append(seg)
    return kept

import whisper, json
from pathlib import Path

model = whisper.load_model("medium")
result = model.transcribe(
    str(Path.home() / "video-pipeline/output/merged_temp.mp4"),
    language="zh", fp16=False,
    initial_prompt="以下是普通话口播视频内容："
)

original = result["segments"]
deduped = remove_duplicates(original)

removed = len(original) - len(deduped)
print(f"✅ 原始片段: {len(original)} 条")
print(f"✅ 去重后: {len(deduped)} 条（移除 {removed} 条重复）")

# 保存去重后的时间段，供 ffmpeg 使用
segments_path = Path.home() / "video-pipeline/output/segments_deduped.json"
with open(segments_path, "w") as f:
    json.dump(deduped, f, ensure_ascii=False, indent=2)

# 同时生成去重后的 SRT
srt_path = Path.home() / "video-pipeline/output/subtitles.srt"
with open(srt_path, "w") as f:
    for i, seg in enumerate(deduped, 1):
        def fmt(s):
            h,m = divmod(int(s),3600); m,sc = divmod(m,60)
            ms = int((s-int(s))*1000)
            return f"{h:02}:{m:02}:{sc:02},{ms:03}"
        f.write(f"{i}\n{fmt(seg['start'])} --> {fmt(seg['end'])}\n{seg['text'].strip()}\n\n")

print(f"✅ 字幕已生成")
