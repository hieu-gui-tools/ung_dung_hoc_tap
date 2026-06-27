import re
from bs4 import BeautifulSoup

with open('tu_vung.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

with open('extracted_links.txt', 'w', encoding='utf-8') as f:
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'tieng-anh' in href:
            f.write(f"TEXT: {a.text.strip()} -> {href}\n")
