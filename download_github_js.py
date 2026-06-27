import requests

url = 'https://raw.githubusercontent.com/MinhMVP/GPLX-600/main/script.js'
r = requests.get(url)
with open('github_script.js', 'w', encoding='utf-8') as f:
    f.write(r.text)

with open('github_preview.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(r.text.split('\n')[:500]))
