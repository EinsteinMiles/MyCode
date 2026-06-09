import urllib.request
import os
import json
import jsonpath

url = 'https://dianying.taobao.com/cityAction.json?activityId&_ksTS=1781014038536_108&jsoncallback=jsonp109&action=cityAction&n_s=new&event_submit_doGetAllRegion=true'

headers = {
    'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
    'Cookie':'cookie2=1c6d10248cdc8976892ac2ebe011dc6e; t=79d164894d01b2df603a5697d9ddcf88; _tb_token_=76e7e5e93333e; cna=cwNMIB6eynoCAQAAAABrRK1Y; thw=cn; wk_cookie2=12b759adfbcdfb284791bfe183b57b5a; wk_unb=UNN4DxKQnbyH7Q%3D%3D; _hvn_lgc_=0; havana_lgc2_0=eyJoaWQiOjMzNTk2OTkwMTIsInNnIjoiMDY4NzM4NmQ3NWM4YmVlY2JmNGQ2OWI4MmI2MWM0ODciLCJzaXRlIjowLCJ0b2tlbiI6IjF1M0o5WnJRSTNQRmZhcnlYbjlIVTR3In0; lgc=sarius1314; cancelledSubSites=empty; dnk=sarius1207; tracknick=sarius1314; sn=; tfstk=gzqEXYqQwMIUt9103-mPu4ZB0rmKb05b-uGSE82odXcnd7izzSh6V9nCy0Pr_7hIRDcB4ulgnTKCpw3oaWnnyyGSObozeSW1GisbpJn-rs1fcY61IRnnKUxk-TAinxBsKE90gNn-qs16530d00FBa4cjrFDi6Y-nZ0VkIADjsYYnq7ciSxDXt0muZOSiexOoZY0HsRctE0cuZ0XaIfHrqbVoqOyiCqFu9hlZ-9gbAyAXQNljiJcwqnJxL2YUTUtJ2lkE8u2K_YkzbvuEG4M2Onq318qQvVQ6W0e_u7zuwZTtY84nxxwdYho0KPZrCu6WzXVLbRqK7KKx8zDro00wE32ZvfugAmjD_AUgdzqLTL-opkZjzj3NE33Sjog0oWJRHRmnE73YVsKKt82YDriVfem0QzV4zgl6wAvY6uER2UunBAlfQO7xNYW41Q91KUL-7NHZGtBvyU3nBAlfQO8JyVrtQj6AH; v=0; _samesite_flag_=true; mtop_partitioned_detect=1; _m_h5_tk=2799f094ca41a5b71eb9da6330645b43_1781018723680; _m_h5_tk_enc=54b3f6f43d47b208d839776a5f6440b0; xlly_s=1; unb=3359699012; uc1=cookie16=UtASsssmPlP%2Ff1IHDsDaPRu%2BPw%3D%3D&cookie15=VFC%2FuZ9ayeYq2g%3D%3D&cookie21=V32FPkk%2FgihF%2FS5nr3O5&existShop=false&pas=0&cookie14=UoYWPA6NN25hGw%3D%3D; uc3=vt3=F8dD1NM367kjPAvor38%3D&lg2=U%2BGCWk%2F75gdr5Q%3D%3D&id2=UNN4DxKQnbyH7Q%3D%3D&nk2=EF8DjBre4FPYjA%3D%3D; csg=727f94e9; ultraCookieBase=1k6S5%2BcxkgQpZDoYF3Dxeydw8sw3UIcsb6qE5QUCCBGQ%2BrcHRP8pYn8Bm6MZY45pAJtaZqJdjlV9DkGdwbzrd6vfSWQh%2BoWzAQeDr3DVA3dnQMJM0HOjMKYFBUIf8st%2F8WkRX1Bv1lM5BrKUgA98D8Iw7koFKS7KviPJ2fYkKh14QHX0u9vHNtqzLiFFigwmKQKCDbzgPxSZyToE7QoQTEqTLWQTSgFtnaC4ZaBFWyLfiWWdly1nIQkNHAq82rjKrh3Nb4d3OBewqAyp67Dogb%2BsdAexx8SNq954%2Fl9ApmgaX6jBL3wUJx10YCAmCagw9ew%3D%3D; cookie17=UNN4DxKQnbyH7Q%3D%3D; skt=c1d473930c3db794; existShop=MTc4MTAxMTU2Mw%3D%3D; uc4=id4=0%40UgQwGjEOcdIDH3sLP7mhJgmVyLrt&nk4=0%40EoZ8lrKsQEWpqUIBZimar5IgqLXL; _cc_=UtASsssmfA%3D%3D; _l_g_=Ug%3D%3D; sg=42a; _nk_=sarius1314; cookie1=BxNVuZO%2B2j8GTX3zGbnCqWdOuMRh%2FPPqGpef9iXbA6k%3D; sgcookie=E1000bG9z4gW2nUaQXn97WQOboGgSPYLbxgt6NG44bLV35%2BcpRQgG9JTd7xV8t6OFhPB%2F0e8KuG4d1T37fWT96R9bCf%2BdCeFaDXArdnBaPnI8ytIr3uMeRaBVxueNsGiDShM; havana_lgc_exp=1812115563633; sdkSilent=1781040363633; havana_sdkSilent=1781040363633; tb_city=110100; tb_cityName="sbG+qQ=="; isg=BF9fYVuOST6jXk0Sy_hb7ieE7rPpxLNmicme0PGtT45VgH8C-ZUGtubWQhD-GIve',
    'referer':'https://dianying.taobao.com/?spm=a1z21.3046609.header.1.7c17112aTZ5C7t&n_s=new'
}

request = urllib.request.Request(url=url,headers=headers)
response = urllib.request.urlopen(request)
content = response.read().decode('utf-8')

content = content.split('(')[1].split(')')[0]

file_path = 'Python/Partice'
name = '4.taopp.json'
file_path = os.path.join(file_path,name)

with open(file_path,'w',encoding='utf=8') as fp:
    fp.write(content)

obj = json.load(open('Python/Partice/4.taopp.json','r',encoding='utf-8'))
region_name = jsonpath.jsonpath(obj,'$..regionName')

print(region_name)