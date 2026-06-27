import requests

url = 'https://dethitracnghiem.vn/wp-admin/admin-ajax.php'

actions = ['iaeb_get_result', 'iaeb_result', 'get_result', 'iaeb_submit_exam']
for action in actions:
    data = {
        'action': action,
        'post_id': '90022',
        'exam_id': '90022'
    }
    r = requests.post(url, data=data)
    print(f"Action {action}: {r.status_code}")
    if r.status_code == 200:
        print(r.text[:200])
