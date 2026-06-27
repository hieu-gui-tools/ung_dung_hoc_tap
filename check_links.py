import requests
from bs4 import BeautifulSoup
import re

url = "https://dethitracnghiem.vn/bang-lai-xe-o-to-hang-b/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

print("All links containing '600' or 'cau-hoi':")
for a in soup.find_all('a', href=True):
    if '600' in a['href'] or 'cau-hoi' in a['href'] or 'ly-thuyet' in a['href']:
        print(a.text.strip(), a['href'])
