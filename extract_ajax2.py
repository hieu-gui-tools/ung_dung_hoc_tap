import re
import urllib.parse

js = open('script.js', encoding='utf-8').read()

# search for ajax setup or data payloads
matches = re.findall(r'(\.ajax\([^)]+\))', js)
for m in matches:
    print(m[:200])

print("---")
# search for any 'action' parameter in the file
for match in re.findall(r'action\s*[=:]\s*[\'\"]?([a-zA-Z0-9_]+)[\'\"]?', js):
    print("Found action:", match)

# search for admin-ajax in string literals
for match in re.findall(r'[\'\"]([^\'\"]*admin-ajax[^\'\"]*)[\'\"]', js):
    print("Found ajax url:", match)

