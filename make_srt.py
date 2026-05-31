import whisper, sys
from pathlib import Path

# 接收语言参数
# python3 make_srt.py zh     → 纯中文字幕
# python3 make_srt.py en     → 纯英文字幕
# python3 make_srt.py zh+en  → 中英双语字幕

mode = sys.argv[1] if len(sys.argv) > 1 else "zh"

model = whisper.load_model("small")

if mode == "en":
    result = model.transcribe(
        str(Path.home() / "video-pipeline/output/merged_temp.mp4"),
        language="zh", fp16=False,
        task="translate",
        initial_prompt="The following is a Chinese video translated to English:"
    )
else:
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

if mode == "zh+en":
    en_result = model.transcribe(
        str(Path.home() / "video-pipeline/output/merged_temp.mp4"),
        language="zh", fp16=False, task="translate"
    )
    en_segs = en_result["segments"]

MAX_ZH_PER_LINE = 16
MAX_EN_PER_LINE = 60

def split_zh(text, start, end):
    if len(text) <= MAX_ZH_PER_LINE:
        return [(text, start, end)]
    chunks = []
    current = ""
    for ch in text:
        current += ch
        if ch in "，。！？、；," and len(current) >= MAX_ZH_PER_LINE // 2:
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    final = []
    for c in chunks:
        while len(c) > MAX_ZH_PER_LINE:
            final.append(c[:MAX_ZH_PER_LINE])
            c = c[MAX_ZH_PER_LINE:]
        if c:
            final.append(c)
    if not final:
        final = [text]
    total = sum(len(c) for c in final)
    dur = end - start
    result, t = [], start
    for c in final:
        seg_dur = dur * len(c) / max(total, 1)
        result.append((c, t, t + seg_dur))
        t += seg_dur
    return result

def split_en(text, zh_segments):
    if len(zh_segments) == 1:
        return [text]
    words = text.split()
    if not words:
        return [""] * len(zh_segments)
    zh_lens = [len(z[0]) for z in zh_segments]
    total_zh = sum(zh_lens)
    result, idx = [], 0
    for i, zl in enumerate(zh_lens):
        count = round(len(words) * zl / max(total_zh, 1))
        if i == len(zh_lens) - 1:
            result.append(" ".join(words[idx:]))
        else:
            result.append(" ".join(words[idx:idx+count]))
            idx += count
    return result

with open(srt_path, "w", encoding="utf-8") as f:
    idx = 1
    for seg in result["segments"]:
        zh_text = seg["text"].strip()
        if mode == "zh+en":
            best_en, best_overlap = "", 0
            for es in en_segs:
                overlap = min(seg["end"], es["end"]) - max(seg["start"], es["start"])
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_en = es["text"].strip()
            zh_segs = split_zh(zh_text, seg["start"], seg["end"])
            en_parts = split_en(best_en, zh_segs)
            for (zh, s, e), en in zip(zh_segs, en_parts):
                f.write(f"{idx}\n{fmt(s)} --> {fmt(e)}\n{zh}\n{en}\n\n")
                idx += 1
        else:
            zh_segs = split_zh(zh_text, seg["start"], seg["end"])
            for (zh, s, e) in zh_segs:
                f.write(f"{idx}\n{fmt(s)} --> {fmt(e)}\n{zh}\n\n")
                idx += 1

print(f"✅ 字幕生成完成（模式: {mode}）")
