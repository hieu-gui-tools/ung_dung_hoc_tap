import requests
import json
from bs4 import BeautifulSoup

url = 'https://dethitracnghiem.vn/bai-thi/de-thi-bo-luat-moi-lai-xe-oto-hang-b-de-1/'
post_id = '90022' # extracted from script

# dummy answers (like choosing A for all)
dummy_answers = ["A"] * 35 # assume max 40 questions
cookie_val = json.dumps({"exam_" + post_id: dummy_answers})

cookies = {
    'iaeb_answered': cookie_val
}

response = requests.get(url, cookies=cookies)
soup = BeautifulSoup(response.text, 'html.parser')

items = soup.find_all('div', class_='iaeb-item')
if not items:
    print("No items found.")
else:
    q1 = items[0]
    # Check if there is any correct answer class or solution
    correct_ans = q1.find('li', class_='iaeb-correct')
    if correct_ans:
        print("Found correct answer via class iaeb-correct:", correct_ans.get('data-answer'))
    else:
        # Just print li's classes
        for li in q1.find_all('li'):
            print(f"li data-answer={li.get('data-answer')} classes={li.get('class')}")
        
        # Print solution content if any
        sol = q1.find('div', class_='iaeb-solution-content')
        if sol:
            print("Solution content:", sol.text.strip())

