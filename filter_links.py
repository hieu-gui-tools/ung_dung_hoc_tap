import json

with open('homepage_links.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open('filtered_links.txt', 'w', encoding='utf-8') as out:
    for line in lines:
        if 'tieng-anh' in line.lower() or 'anh' in line.lower() or 'english' in line.lower():
            out.write(line)
