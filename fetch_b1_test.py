import requests
from bs4 import BeautifulSoup
import re

url = "https://vi.englishteststore.net/vstep-b1-b2-c1/20-de-luyen-thi-tieng-anh-b1-kem-dap-an/"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)

if r.status_code == 200:
    soup = BeautifulSoup(r.text, 'html.parser')
    links = []
    for a in soup.find_all('a', href=True):
        if 'practice-test' in a['href'] or 'mock-test' in a['href']:
            links.append(a['href'])
            
    if links:
        test_url = links[0]
        print(f"Test URL: {test_url}")
        
        # Test one URL
        r2 = requests.get(test_url, headers=headers)
        soup2 = BeautifulSoup(r2.text, 'html.parser')
        with open('test_page.txt', 'w', encoding='utf-8') as f:
            for p in soup2.find_all('p'):
                f.write(p.text + '\n')
            f.write('\n\n---ALL TAGS---\n\n')
            for tag in soup2.find('body').find_all(['p', 'div', 'span', 'li', 'h3', 'table']):
                cls = tag.get('class', [])
                if cls:
                    f.write(f"<{tag.name} class='{cls}'>: {tag.text[:50]}\n")
