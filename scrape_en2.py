import requests
from bs4 import BeautifulSoup

def get_tests(url):
    print(f"Fetching {url}")
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    # Try to find the main content div
    main = soup.find('main') or soup.find(id='content') or soup
    
    tests = []
    # Usually test links are in h2, h3 or specific post classes
    for a in main.find_all('a', href=True):
        href = a['href']
        text = a.text.strip()
        # English tests often have /tu-vung-tieng-anh/ or /ngu-phap-tieng-anh/ or /tieng-anh/
        if text and ('tieng-anh' in href or 'bai-thi' in href or 'de-thi' in href):
            # Exclude sidebar links usually found by checking if it's inside an article or post-title
            parent = a.parent
            if parent.name in ['h2', 'h3', 'h4'] or 'post-title' in parent.get('class', []):
                if text not in [t[0] for t in tests]:
                    tests.append((text, href))
    return tests

t1 = get_tests("https://dethitracnghiem.vn/kien-thuc/tieng-anh/tu-vung/")
t2 = get_tests("https://dethitracnghiem.vn/kien-thuc/tieng-anh/ngu-phap/")

all_tests = t1 + t2
with open('en_tests_real.txt', 'w', encoding='utf-8') as f:
    for t in all_tests:
        f.write(f"{t[0]} -> {t[1]}\n")
print(f"Found {len(all_tests)} tests.")
