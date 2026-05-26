import sys, re
from pathlib import Path

FONT = "/System/Library/Fonts/STHeiti Medium.ttc"
FONTSIZE = 44
FONTSIZE_EN = 28
MARGIN_V = 150
MAX_ZH = 14
MAX_EN = 30

style = sys.argv[1] if len(sys.argv) > 1 else "highlight"
keywords_raw = sys.argv[2] if len(sys.argv) > 2 else ""
lang = sys.argv[3] if len(sys.argv) > 3 else "zh"
keywords = [w.strip() for w in re.split(r'[,，\s]+', keywords_raw) if w.strip()]

def parse_srt(path):
    blocks, current = [], {}
    lines_buf = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line.isdigit():
            if current:
                current["text"] = lines_buf
                blocks.append(current)
            current = {"id": int(line)}
            lines_buf = []
        elif "-->" in line:
            def to_sec(t):
                h,m,s = t.replace(",",".").split(":")
                return int(h)*3600+int(m)*60+float(s)
            s,e = line.split(" --> ")
            current["start"] = to_sec(s.strip())
            current["end"] = to_sec(e.strip())
        elif line and "start" in current:
            lines_buf.append(line)
    if current:
        current["text"] = lines_buf
        blocks.append(current)
    return blocks

def split_single(text, start, end):
    """单语言：强制单行14字"""
    is_chinese = bool(re.search(r"[\u4e00-\u9fff]", text))
    max_len = MAX_ZH if is_chinese else MAX_EN
    if len(text) <= max_len:
        return [{"text": text, "start": start, "end": end}]

    parts = re.split(r'([，。！？,!?、；;])', text)
    chunks, current = [], ""
    for p in parts:
        if p in '，。！？,!?、；;':
            current += p
            if current.strip(): chunks.append(current.strip())
            current = ""
        else:
            if len(current)+len(p) > max_len and current:
                chunks.append(current.strip())
                current = p
            else:
                current += p
    if current.strip(): chunks.append(current.strip())

    final = []
    for c in chunks:
        while len(c) > max_len:
            final.append(c[:max_len])
            c = c[max_len:]
        if c: final.append(c)

    if not final:
        return [{"text": text[:max_len], "start": start, "end": end}]

    total = sum(len(c) for c in final)
    dur = end - start
    result, t = [], start
    for c in final:
        d = dur * len(c)/max(total,1)
        result.append({"text": c, "start": t, "end": t+d})
        t += d
    return result

def sec_to_ass(s):
    h,m = divmod(int(s),3600); m,sc = divmod(m,60)
    cs = int((s-int(s))*100)
    return f"{h}:{m:02}:{sc:02}.{cs:02}"

def highlight(text):
    styled, i = "", 0
    while i < len(text):
        matched = False
        for kw in keywords:
            if text[i:i+len(kw)] == kw:
                styled += r"{\c&H0000FFFF&\b1}" + kw + r"{\c&H00FFFFFF&\b0}"
                i += len(kw)
                matched = True
                break
        if not matched:
            styled += text[i]; i += 1
    return styled

srt = Path.home() / "video-pipeline/output/subtitles.srt"
ass = Path.home() / "video-pipeline/output/subtitles.ass"
subs = parse_srt(srt)

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

if lang == "zh+en":
    # 双语：中文14字限制+高亮，英文30字限制在下方小字
    for sub in subs:
        lines = sub["text"]
        zh_text = lines[0] if lines else ""
        en_text = lines[1] if len(lines) > 1 else ""
        s = sec_to_ass(sub["start"])
        e = sec_to_ass(sub["end"])

        # 中文截断到14字
        if len(zh_text) > MAX_ZH:
            zh_text = zh_text[:MAX_ZH]

        # 中文高亮
        if style == "highlight":
            zh_styled = highlight(zh_text)
        else:
            zh_styled = zh_text

        # 英文截断到30字
        if len(en_text) > MAX_EN:
            en_text = en_text[:MAX_EN]

        # 组合：中文大字 + 换行 + 英文小字白色
        if en_text:
            combined = zh_styled + f"\\N{{\\fs{FONTSIZE_EN}\\c&H00FFFFFF&}}" + en_text
        else:
            combined = zh_styled

        events.append(f"Dialogue: 0,{s},{e},Default,,0,0,0,,{combined}")

else:
    # 单语：强制单行
    all_lines = []
    for sub in subs:
        text = sub["text"][0] if sub["text"] else ""
        all_lines.extend(split_single(text, sub["start"], sub["end"]))

    for line in all_lines:
        text = line["text"]
        s = sec_to_ass(line["start"])
        e = sec_to_ass(line["end"])
        if style == "highlight":
            text = highlight(text)
        elif style == "fade":
            fd = min(0.3, (line["end"]-line["start"])/3)
            text = f"{{\\fad({int(fd*1000)},{int(fd*1000)})}}" + text
        elif style == "karaoke":
            text = r"{\c&H0000FFFF&}" + text
        events.append(f"Dialogue: 0,{s},{e},Default,,0,0,0,,{text}")

with open(ass, "w", encoding="utf-8") as f:
    f.write(header + "\n".join(events))

print(f"✅ {lang} {style} 字幕完成，共{len(events)}条")
