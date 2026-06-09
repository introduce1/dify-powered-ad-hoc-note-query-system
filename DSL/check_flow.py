import yaml
d = yaml.safe_load(open(r'c:\Users\17375\Desktop\现阶段工程文件\DSL\随记随查_宽松版.yml', encoding='utf-8'))
for n in d['workflow']['graph']['nodes']:
    print(f"{n['id']} {n['data']['title']}")
print('---')
for e in d['workflow']['graph']['edges']:
    print(f"{e['source']}({e['sourceHandle']}) -> {e['target']}")
