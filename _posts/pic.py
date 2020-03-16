#coding=utf-8
import re
import requests
fname = "2019-11-29-MIPS_basic.markdown"
with open(fname,"r") as f:
    data = f.read()

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:74.0) Gecko/20100101 Firefox/74.0"
}
res = re.findall(r"(https://.*\.png)",data)
cnt = 1
for url in res:
    picdata = requests.get(url,headers=headers).content
    print url
    newname = "IMG/MIPS101/mips"+str(cnt)+".png"

