"""Audience-facing polish for the dashboard:
  1) drop the "답" labels on the summary boxes
  2) drop the "의사결정 요청" block (internal ask, not for the audience)
  3) convert sentence endings from "~이다/~한다" to noun-ending (개조식) style
Applies to exec_render_html.py, which is then re-run to rebuild the HTML.
"""
import re, sys
from pathlib import Path

R = Path(__file__).resolve().parent / "exec_render_html.py"
s = R.read_text(encoding="utf-8")
orig = s

# ---------------------------------------------------------------- 1. remove the "답" labels
n_ans = len(re.findall(r'<div class=k>답</div>\s*', s))
s = re.sub(r'<div class=k>답</div>\s*', '', s)

# ---------------------------------------------------------------- 2. remove the decision-request block
start = s.find('<div class="ans"><div class=k>의사결정 요청</div>')
if start == -1:
    print("WARN: decision block not found"); n_dec = 0
else:
    end = s.find('</tbody></table></div>', start)
    assert end != -1, "decision block end not found"
    s = s[:start] + s[end + len('</tbody></table></div>'):]
    n_dec = 1

# ---------------------------------------------------------------- 3. tone: verb endings -> noun endings
OVERRIDE = {
    "싸다": "저렴", "같다": "동일", "본다": "판단", "맞다": "맞음", "아니다": "아님",
    "느리다": "느림", "치열하다": "치열", "불리하다": "불리", "유리하다": "유리",
    "가능하다": "가능", "동일하다": "동일", "현실적이다": "현실적", "어렵다": "어려움",
    "다르다": "다름", "크다": "큼", "낮다": "낮음", "있다": "있음", "없다": "없음",
    "구조다": "구조", "노드다": "노드", "모양이다": "모양", "시장이다": "시장",
    "하락이다": "하락", "것이다": "것", "때문이다": "때문", "시간뿐이다": "시간뿐",
    "않다": "않음", "않는다": "않음", "잡는다": "잡음", "재계산됩니다": "재계산",
    "않았습니다": "미반영", "작습니다": "작음", "해였습니다": "해", "뿐입니다": "뿐",
    "만듭니다": "만듦", "됩니다": "됨", "납니다": "남", "입니다": "임",
}
RULES = [("됐다", "됨"), ("었다", "었음"), ("았다", "았음"), ("였다", "였음"), ("했다", "함"),
         ("진다", "짐"), ("된다", "됨"), ("친다", "침"), ("룬다", "룸"), ("온다", "옴"),
         ("난다", "남"), ("든다", "듦"), ("린다", "림"), ("긴다", "김"), ("는다", "음"),
         ("한다", "함"), ("이다", "임")]

pat = re.compile(r'([가-힣]{1,8}?(?:다|니다))(?=[.。]|<|\s*—|\s*\(|\s*$)', re.M)
changed, unmapped = [], set()

def conv(tok):
    if tok in OVERRIDE:
        return OVERRIDE[tok]
    for suf, rep in RULES:
        if tok.endswith(suf) and len(tok) > len(suf):
            return tok[: -len(suf)] + rep
        if tok == suf:
            return rep
    unmapped.add(tok)
    return None

def repl(m):
    tok = m.group(1)
    new = conv(tok)
    if new is None or new == tok:
        return tok
    changed.append((tok, new))
    return new

s = pat.sub(repl, s)

print(f"제거: '답' 라벨 {n_ans}개, 의사결정 요청 블록 {n_dec}개")
print(f"종결 표현 변환 {len(changed)}곳")
import collections
for (a, b), n in collections.Counter(changed).most_common():
    print(f"   {a:12s} -> {b}   ({n})")
if unmapped:
    print("\n미변환(확인 필요):", sorted(unmapped))

R.write_text(s, encoding="utf-8")
print("\nwrote exec_render_html.py")
