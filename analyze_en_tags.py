import re
from bs4 import BeautifulSoup

with open('en_test_content.html', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f.read(), 'html.parser')

main = soup.find('main') or soup.find(id='content') or soup

with open('en_test_all_tags.txt', 'w', encoding='utf-8') as out:
    for tag in main.find_all(True):
        if tag.name not in ['span', 'br', 'strong', 'em', 'a', 'img', 'b', 'i', 'u']:
            # only print structural tags
            cls = tag.get('class', '')
            out.write(f"<{tag.name} class='{cls}'>\n")
