import requests
from bs4 import BeautifulSoup

url = "https://tracnghiemcongchuc.com/de-thi-tieng-anh-cong-chuc-trinh-do-b1/30-cau-trac-nghiem-tieng-anh-bac-3-b1-so-13-523.html"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

with open('tracnghiemcongchuc_test.txt', 'w', encoding='utf-8') as f:
    for p in soup.find_all(['p', 'div', 'h3', 'span']):
        text = p.get_text(strip=True)
        if len(text) > 20:
            f.write(text + "\n")
