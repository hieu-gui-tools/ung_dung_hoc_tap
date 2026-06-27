import requests

url = "https://dethitracnghiem.vn/kien-thuc/tieng-anh/tu-vung/"
r = requests.get(url)
with open('tu_vung.html', 'w', encoding='utf-8') as f:
    f.write(r.text)
