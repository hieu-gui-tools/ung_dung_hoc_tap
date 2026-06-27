import requests

url = 'https://dethitracnghiem.vn/wp-content/cache/min/1/wp-content/plugins/iauto-exam-buildup/view/js/script.js?ver=1778835965'
r = requests.get(url)
with open('script.js', 'w', encoding='utf-8') as f:
    f.write(r.text)
