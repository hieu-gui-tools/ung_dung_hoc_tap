import requests
from bs4 import BeautifulSoup
import re

url = "https://dethitracnghiem.vn/kien-thuc/tieng-anh/tu-vung/"
r = requests.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

tests = []
for a in soup.find_all('a', href=True):
    if '/bai-thi/' in a['href'] or '/de-thi/' in a['href'] or '/trac-nghiem' in a['href']:
        text = a.text.strip()
        if text and len(text) > 10:
            tests.append((text, a['href']))

with open('en_tests.txt', 'w', encoding='utf-8') as f:
    f.write("=== English Tests (Tu Vung) ===\n")
    for t in tests:
        f.write(f"{t[0]} -> {t[1]}\n")

# Fetch the first test to see structure
if tests:
    # Filter for actual tests
    valid_tests = [t for t in tests if 'trac-nghiem' in t[1] or 'bai-thi' in t[1]]
    if valid_tests:
        test_url = valid_tests[0][1]
        with open('en_tests.txt', 'a', encoding='utf-8') as f:
            f.write(f"\n=== Fetching test {test_url} ===\n")
        tr = requests.get(test_url)
        tsoup = BeautifulSoup(tr.text, 'html.parser')
        
        items = tsoup.find_all('div', class_=re.compile(r'iaeb-item'))
        with open('en_tests.txt', 'a', encoding='utf-8') as f:
            f.write(f"Found {len(items)} questions with iaeb-item\n")
        
        if len(items) == 0:
            # Maybe another class?
            q_divs = tsoup.find_all('div', class_=re.compile(r'question'))
            with open('en_tests.txt', 'a', encoding='utf-8') as f:
                f.write(f"Found {len(q_divs)} elements with 'question' in class\n")
