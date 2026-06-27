import requests
from bs4 import BeautifulSoup
import re

url = "https://dethitracnghiem.vn/bang-lai-xe-o-to-hang-b/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

with open('links.txt', 'w', encoding='utf-8') as f:
    for a in soup.find_all('a', href=True):
        f.write(f"{a.text.strip()} | {a['href']}\n")
