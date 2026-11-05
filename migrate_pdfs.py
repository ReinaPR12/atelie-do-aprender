import os,re,json,html,hashlib,urllib.parse,urllib.request,concurrent.futures,subprocess,time,requests
from pathlib import Path
ROOT=Path('/Users/pietroreina/Projects/atelie-do-aprender')
BASE='https://cantinhodaprofjuliana.com.br/'
out=ROOT/'pdfs';out.mkdir(exist_ok=True)
headers={'User-Agent':'Mozilla/5.0 (compatible; EducationalArchive/1.0)'}
def request(url):
 return requests.get(url,headers=headers,timeout=45)
page=request(BASE).text
raw=re.findall(r'/pdfs/[a-zA-Z0-9_./%+()~=-]+[.]pdf',page,re.I)
raw+=re.findall(r'https?://cantinhodaprofjuliana[.]com[.]br/pdfs/[a-zA-Z0-9_./%+()~=-]+[.]pdf',page,re.I)
urls=set()
for path in raw:
 path=html.unescape(path).replace('\\/','/')
 url=urllib.parse.urljoin(BASE,path)
 if urllib.parse.urlparse(url).netloc=='cantinhodaprofjuliana.com.br':urls.add(url)
print('discovered',len(urls),flush=True)
items=[]
def derive(url):
 p=urllib.parse.urlparse(url).path
 slug=Path(p).stem
 idx=page.find(url)
 if idx<0:idx=page.find(p)
 snippet=page[max(0,idx-2500):idx]
 titles=re.findall(r'<h[234][^>]*>(.*?)</h[234]>',snippet,re.I|re.S)
 title=re.sub('<[^>]*>',' ',titles[-1]).strip() if titles else ''
 title=html.unescape(title)
 if not title or len(title)>100:title=slug.replace('-',' ').replace('_',' ').title()
 group=Path(p).parent.name
 cat='Artes' if group=='artes' else 'Natal' if group=='natal' else 'Apostilas' if group=='leona' else 'Atividades'
 return p, title,cat
def fetch(url):
 path,title,cat=derive(url)
 rel=path.lstrip('/')
 if '..' in Path(rel).parts:return dict(url=url,status='invalid_path')
 dest=ROOT/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 try:
  if dest.exists() and dest.stat().st_size>100:
   blob=dest.read_bytes()
  else:
   blob=request(url).content
   if len(blob)>30_000_000:raise ValueError('file exceeds 30MB limit')
  if not blob.startswith(b'%PDF-'):raise ValueError('not PDF: '+repr(blob[:40]))
  if not dest.exists():dest.write_bytes(blob)
  return dict(title=title,category=cat,path=rel,url=url,bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest(),status='ok')
 except Exception as exc:return dict(title=title,category=cat,url=url,path=rel,status='error',error=str(exc))
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 for i,res in enumerate(ex.map(fetch,sorted(urls)),1):
  items.append(res)
  if i%10==0 or i==len(urls):print('downloaded',i,'/',len(urls),'ok',sum(x['status']=='ok' for x in items),flush=True)
items.sort(key=lambda x:(x.get('category',''),x.get('title','')))
(ROOT/'pdf-manifest.json').write_text(json.dumps({'source':BASE,'discovered':len(urls),'items':items},ensure_ascii=False,indent=2))
catalog=[{'name':x['title'],'cat':x['category'],'url':'./'+x['path'],'size':x['bytes']} for x in items if x['status']=='ok']
(ROOT/'pdf-catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
print('RESULT',json.dumps({'total':len(urls),'downloaded':len(catalog),'failed':[x['url'] for x in items if x['status']!='ok'],'bytes':sum(x['size'] for x in catalog),'categories':{c:sum(x['cat']==c for x in catalog) for c in set(x['cat'] for x in catalog)}},ensure_ascii=False),flush=True)
