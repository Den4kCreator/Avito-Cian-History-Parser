import re

with open('log.log', encoding='utf-8') as f:
    ads = [eval(ad) for ad in re.findall(r"{'ad_name'.+}", f.read())]