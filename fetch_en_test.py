import requests
from bs4 import BeautifulSoup
import re

url = "https://dethitracnghiem.vn/chu-de-tu-vung-emotion-cam-xuc-trong-tieng-anh/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

items = soup.find_all('div', class_=re.compile(r'iaeb-item'))
print(f"Found {len(items)} questions with iaeb-item")
if items:
    q_div = items[0].find('div', class_=re.compile('iaeb-quiz'))
    if q_div:
        print("Q:", q_div.text.strip())
        opts = items[0].find_all('div', class_=re.compile('iaeb-answer'))
        print("Opts:", [o.text.strip() for o in opts])
