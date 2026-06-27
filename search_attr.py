import re
html = open('output.html', encoding='utf-8').read()

matches = re.findall(r'data-[a-zA-Z\-]*[\'\"]?[:=]\s*[\'\"]?[A-D][\'\"]?', html)
print(set(matches))
matches = re.findall(r'correct.*?[\'\"]?[:=]\s*[\'\"]?[A-D][\'\"]?', html, re.IGNORECASE)
print(set(matches))
