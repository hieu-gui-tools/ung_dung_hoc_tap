import requests
from bs4 import BeautifulSoup

url = "https://dethitracnghiem.vn/chu-de-tu-vung-emotion-cam-xuc-trong-tieng-anh/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

with open('en_test_tables.txt', 'w', encoding='utf-8') as f:
    for i, table in enumerate(soup.find_all('table')):
        f.write(f"--- Table {i} ---\n")
        for row in table.find_all('tr'):
            cols = [col.text.strip() for col in row.find_all(['th', 'td'])]
            f.write(" | ".join(cols) + "\n")
