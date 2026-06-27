import requests
from bs4 import BeautifulSoup
import re

url = "https://tracnghiemcongchuc.com/de-thi-tieng-anh-cong-chuc-trinh-do-b1/30-cau-trac-nghiem-tieng-anh-bac-3-b1-so-13-523.html"
headers = {'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

with open('trac_answers.txt', 'w', encoding='utf-8') as f:
    for script in soup.find_all('script'):
        if script.string and ('answer' in script.string.lower() or 'dap_an' in script.string.lower() or 'dapan' in script.string.lower()):
            f.write(script.string + "\n\n")
            
    # Also look at input fields or data attributes
    for inp in soup.find_all('input'):
        f.write(str(inp) + '\n')
