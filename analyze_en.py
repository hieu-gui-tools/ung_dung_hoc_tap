import re
from bs4 import BeautifulSoup

with open('en_test_content.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

main = soup.find('main') or soup.find(id='content') or soup

with open('analyze_en_out.txt', 'w', encoding='utf-8') as out:
    out.write("First 10 p tags in main:\n")
    for i, p in enumerate(main.find_all('p')[:10]):
        out.write(f"P{i}: {p.text.strip()}\n")
        
    out.write("\nLook for typical question prefixes:\n")
    for p in main.find_all('p'):
        text = p.text.strip()
        if re.match(r'^(Câu|Question)\s*\d+[:\.]', text, re.IGNORECASE) or len(text) > 5 and text[0].isdigit() and text[1] in '.:':
            out.write(f"Found Q: {text}\n")
    
    out.write("\nCheck if there are ordered lists:\n")
    for ol in main.find_all('ol'):
        out.write(f"OL with {len(ol.find_all('li'))} items\n")
