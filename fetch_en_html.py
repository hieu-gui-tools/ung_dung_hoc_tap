import requests

url = "https://dethitracnghiem.vn/chu-de-tu-vung-emotion-cam-xuc-trong-tieng-anh/"
r = requests.get(url)
with open('en_test_content.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
