import requests

url = 'https://raw.githubusercontent.com/MinhMVP/GPLX-600/main/script.js'
r = requests.get(url)
with open('github_script.js', 'w', encoding='utf-8') as f:
    f.write(r.text)

print("Downloaded github_script.js. Extracting keys...")
lines = r.text.split('\n')
for i, line in enumerate(lines[:50]):
    print(f"{i}: {line[:200]}")
