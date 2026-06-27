import re

js = open('script.js', encoding='utf-8').read()

# search for ajax calls
matches = re.findall(r'action\s*:\s*[\'\"]([^\'\"]+)[\'\"]', js)
print("Actions in JS:", set(matches))
