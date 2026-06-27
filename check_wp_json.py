import requests

url = 'https://dethitracnghiem.vn/wp-json/wp/v2/posts/90022'
r = requests.get(url)
if r.status_code == 200:
    data = r.json()
    content = data.get('content', {}).get('rendered', '')
    print(content[:500])
    # Also save to file
    with open('post.json', 'w', encoding='utf-8') as f:
        f.write(r.text)
else:
    print("Status:", r.status_code)
