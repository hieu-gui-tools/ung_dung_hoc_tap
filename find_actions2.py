import re

js = open('script.js', encoding='utf-8').read()
actions = set(re.findall(r'action[=:][\'\"\s]*([a-zA-Z0-9_]+)', js))
print("Actions in JS:", actions)
