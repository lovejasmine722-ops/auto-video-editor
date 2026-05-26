import sys, re
from pathlib import Path

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
FONTSIZE = 44
MARGIN_V = 150
MAX_ZH = 14
MAX_EN = 30

style = sys.argv[1] if len(sys.argv) > 1 else "highlight"
keywords_raw = sys.argv[2] if len(sys.argv) > 2 else ""
keywords = [w.strip() for w in re.split(r'[,，\s]+', keywords_raw) if w.strip()]

def parse_srt(path):
    blocks, current = [], {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.isdigit():
            if current: blocks.append(current)
            current = {"id": int(line)}
        elif "-->" in line:
            def to_sec(t):
                h,m,s = t.replace(",",".").split(":")
                return int(h)*3600+int(m)*60+float(s)
            s,e = line.split(" --> ")
            current["start"] = to_sec(s.strip())
            current["end"] = to_sec(e.strip())
        elif line and "start" in current and "text" not in current:
            current["text"] = line
    if current: blocks.append(current)
    return blocks

def split_to_single_lines(text, start, end):
    """强制每条字幕只有一行，超过MAX_ZH字拆成多条"""
    is_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    max_len = MAX_ZH if is_chinese else MAX_EN

    # 先按标点切割
    parts = re.split(r'([，。！？,!?、；;])', text)
    chunks = []
    current = ""
    for p in parts:
        if p in '，。！？,!?、；;':
            current += p
            if current.strip():
                chunks.append(current.strip())
            current = ""
        else:
            if len(current) + len(p) > max_len and current:
                chunks.append(current.strip())
                current = p
            else:
                current += p
    if current.strip():
        chunks.append(current.strip())

    # 再按字数强制截断
    final_chunks = []
    for chunk in chunks:
        while len(chunk) > max_len:
            final_chunks.append(chunk[:max_len])
            chunk = chunk[max_len:]
        if chunk:
            final_chunks.append(chunk)

    if not final_chunks:
        return [{"text": text[:max_len], "start": start, "end": end}]

    # 按字数比例分配时间
    total = sum(len(c) for c in final_chunks)
    duration = end - start
    result = []
    t = start
    for chunk in final_chunks:
        ratio = len(chunk) / max(total, 1)
        seg_dur = duration * ratio
        result.append({"text": chunk, "start": t, "end": t + seg_dur})
        t += seg_dur
    return result

def sec_to_ass(s):
    h,m = divmod(int(s),3600); m,sc = divmod(m,60)
    cs = int((s-int(s))*100)
    return f"{h}:{m:02}:{sc:02}.{cs:02}"

def highlight_text(text):
    styled = ""
    i = 0
    while i < len(text):
        matched = False
        for kw in keywords:
            if text[i:i+len(kw)] == kw:
                styled += r"{\c&H0000FFFF&\b1}" + kw + r"{\c&H00FFFFFF&\b0}"
                i += len(kw)
                matched = True
                break
        if not matched:
            styled += text[i]
            i += 1
    return styled

srt = Path.home() / "video-pipeline/output/subtitles.srt"
ass = Path.home() / "video-pipeline/output/subtitles.ass"
subs = parse_srt(srt)

# 拆分成单行字幕
all_lines = []
for sub in subs:
    lines = split_to_single_lines(sub["text"], sub["start"], sub["end"])
    all_lines.extend(lines)

print(f"✅ 原始: {len(subs)}条 → 单行: {len(all_lines)}条")

header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,STHeiti Medium,{FONTSIZE},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,1,2,1,2,20,20,{MARGIN_V},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""

events = []
for line in all_lines:
    text = line["text"]
    s = sec_to_ass(line["start"])
    e = sec_to_ass(line["end"])

    if style == "highlight":
        styled = highlight_text(text)
    elif style == "fade":
        dur = line["end"] - line["start"]
        fd = min(0.3, dur/3)
        styled = f"{{\\fad({int(fd*1000)},{int(fd*1000)})}}" + text
    elif style == "karaoke":
        styled = r"{\c&H0000FFFF&}" + text
    else:
        styled = text

    events.append(f"Dialogue: 0,{s},{e},Default,,0,0,0,,{styled}")

with open(ass, "w", encoding="utf-8") as f:
    f.write(header + "\n".join(events))

print(f"✅ {style} 字幕生成完成，关键词:{keywords}")
