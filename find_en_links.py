import requests
from bs4 import BeautifulSoup

url = "https://dethitracnghiem.vn/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

with open('homepage_links.txt', 'w', encoding='utf-8') as f:
    for a in soup.find_all('a', href=True):
        href = a['href']
        if 'tieng-anh' in href:
            f.write(f"{a.text.strip()} -> {href}\n")
            
    f.write("\nALL CATEGORIES:\n")
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.count('/') >= 3 and 'dethitracnghiem.vn' in href:
            f.write(f"{a.text.strip()} -> {href}\n")
