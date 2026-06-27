import re
from bs4 import BeautifulSoup

with open('en_test_content.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

with open('analyze_en_ans.txt', 'w', encoding='utf-8') as out:
    for p in soup.find_all('p'):
        text = p.text.strip()
        if re.search(r'đáp án|answer', text, re.IGNORECASE):
            out.write(f"Found ans text: {text}\n")
    
    # Also check if there are divs with id containing answer
    for div in soup.find_all('div', id=re.compile(r'answer|dap-an', re.I)):
        out.write(f"Div ID {div['id']}\n")
