import re

html = open('output.html', encoding='utf-8').read()

# Look for arrays like ["A", "B", "C"] or similar
matches = re.findall(r'\[[\"\'A-D\s,]+\]', html)
for m in matches:
    if len(m) > 10 and 'A' in m:
        print("Found array:", m[:200])

# Look for 'answer', 'correct' strings anywhere in JSON format
matches = re.findall(r'\{[^\}]*(?:answer|correct)[^\}]*\}', html, re.IGNORECASE)
for m in matches[:10]:
    if 'A' in m or 'B' in m or 'C' in m or 'D' in m:
        print("Found JSON:", m[:200])
