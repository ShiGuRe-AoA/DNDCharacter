import argparse,csv,hashlib,re
from pathlib import Path
from lxml import html,etree

CLASS = {
 '野蛮人':('barbarian','Barbarian',12,''),'吟游诗人':('bard','Bard',8,'cha'),
 '牧师':('cleric','Cleric',8,'wis'),'德鲁伊':('druid','Druid',8,'wis'),
 '战士':('fighter','Fighter',10,''),'武僧':('monk','Monk',8,''),
 '圣武士':('paladin','Paladin',10,'cha'),'游侠':('ranger','Ranger',10,'wis'),
 '游荡者':('rogue','Rogue',8,''),'术士':('sorcerer','Sorcerer',6,'cha'),
 '魔契师':('warlock','Warlock',8,'cha'),'法师':('wizard','Wizard',6,'int'),
 '奇械师':('artificer','Artificer',8,'int')
}
LEVEL=re.compile(r'^(?:第\s*)?(\d{1,2})\s*级\s*[:：]\s*(.+)$')
NUM={'一':'1','两':'2','二':'2','三':'3','四':'4','五':'5','六':'6','七':'7','八':'8','九':'9','十':'10'}
ABIL={'力量':'str','敏捷':'dex','体质':'con','智力':'int','感知':'wis','魅力':'cha'}
def norm(value): return ' '.join(value.split())
def text(e): return norm(e.text_content())
def bilingual(label):
 match=re.search(r'(?<=[\u3400-\u9fff）】])\s*(?=[A-Za-z])',label)
 return label[:match.start()].strip()+' '+label[match.end():].strip() if match else label
def read(path):
 b=path.read_bytes()
 encoding='utf-8-sig' if b.startswith(b'\xef\xbb\xbf') or re.search(rb'charset=["\']?utf-8',b[:2048],re.I) else 'gb18030'
 return html.fromstring(b.decode(encoding,errors='replace'))
def digest(value): return hashlib.sha256(value.encode()).hexdigest()[:18]
def layout_text(element):
 for br in element.xpath('.//br'):
  br.tail='\n'+(br.tail or '')
 return '\n'.join(norm(line) for line in element.text_content().splitlines() if norm(line))
def features(doc):
 markers=[]
 for element in doc.xpath('//font[@color] | //h3 | //h4 | //h5 | //strong'):
  if element.tag=='font' and element.get('color','').lower() not in ('#800000','#d08c36'): continue
  match=LEVEL.fullmatch(text(element))
  if not match or not 1<=int(match[1])<=20 or len(match[2])>100: continue
  if any(element in el.iterancestors() or el in element.iterancestors() for el,_ in markers):continue
  markers.append((element,match))
 markers={element:match for element,match in markers}
 if not markers:return []
 out=[]; chunks=[]; active=None
 def add(value):
  if active and value: chunks.append(value)
 def flush():
  if active:
   body='\n'.join(norm(line) for line in ''.join(chunks).splitlines() if norm(line))
   if body:out.append((int(active[1]),bilingual(active[2]),body))
 def scan(el):
  nonlocal active,chunks
  if el in markers:
   flush(); active=markers[el];chunks=[];return
  if not isinstance(el.tag,str) or el.tag in ('script','style','img','nav'):return
  if el.tag in ('h1','h2','h3') and active and not any(m in el.iterdescendants() for m in markers):
   flush();active=None;chunks=[]
  if el.tag in ('p','br','li','tr','h4','h5','div','table'): add('\n')
  if el.tag in ('td','th'):add(' | ')
  add(el.text)
  for child in el:
   scan(child);add(child.tail)
  if el.tag in ('p','li','tr','div'):add('\n')
 scan(doc);flush();return out

def resource(name,body,ruleset,owner):
 flat=norm(body)
 if owner=='fighter' and ruleset=='2024':
  for part,uses,recovery in [
   ('Second Wind','1:2;4:3;10:4','短休恢复1次；长休全部恢复'),
   ('Action Surge','1:1;17:2','短休或长休全部恢复'),
   ('Indomitable','1:1;13:2;17:3','长休全部恢复')]:
   if name.endswith(part):return '',uses,recovery,'curated'
 candidates=[]
 for m in re.finditer(r'(?:使用次数|次数)\s*(?:等于|等同于|等同)\s*(?:你的)?(熟练加值|[力量敏捷体质智力感知魅]{2}调整值)(?:\s*[（(]\s*(?:至少|最少|最低|最小值为)\s*\+?([1一])\s*次?\s*[）)])?',flat):
  label=m[1]; key='pb' if label=='熟练加值' else ABIL.get(label[:2])
  if key:candidates.append('max(1,@'+key+')' if m[2] else '@'+key)
 for m in re.finditer(r'你可以(?:使用此特性|使用该特性|这么做|使用此能力)([1-9一两二三四五六七八九十])次',flat):
  candidates.append(NUM.get(m[1],m[1]))
 for m in re.finditer(r'你(?:使用此特性后，)?必须在完成(?:一次)?(?:短休或长休|长休|短休)后才能再次使用',flat):
  candidates.append('1')
 rests=[p for p in re.split(r'[。；\n]',body) if re.search(r'长休|短休',p) and re.search(r'次数|再次使用|重获',p)]
 recovery='；'.join(dict.fromkeys(norm(p) for p in rests))
 options=set(candidates)
 if len(options)==1 and not re.search(r'(?:级起|额外使用次数|特性表.*次数|使用次数.*见表)',flat):
  return options.pop(),'',recovery,'auto_extracted'
 return '','',recovery,'manual_review' if rests or candidates else 'not_detected'

def run(root,out):
 out.mkdir(parents=True,exist_ok=True)
 classes=[];subclasses=[];base=[];subs=[];audit=[]
 books={'玩家手册2024':'core','艾伯伦：奇械锻炉':'official_supplement','被遗忘的国度':'official_supplement','鸦阁魔域：魔障深藏':'official_supplement'}
 for cn,(cid,en,die,ability) in CLASS.items():
  path=root/'玩家手册2024'/'角色职业'/cn/(cn+'.htm')
  if cid=='artificer':path=root/'艾伯伦：奇械锻炉'/'第一章'/'奇械师.htm'
  if not path.exists():raise ValueError(path)
  rel=path.relative_to(root).as_posix(); book=rel.split('/')[0]
  classes.append(dict(id=cid,name=cn,english_name=en,ruleset='2024',source=book,source_type=books[book],hit_die=die,casting_ability=ability,source_path=rel))
  for level,name,body in features(read(path)):
   uses,progression,recovery,status=resource(name,body,'2024',cid)
   base.append(dict(id='class-feature-'+digest(cid+'|'+str(level)+'|'+name),class_id=cid,name=name,level=level,uses=uses,uses_by_level=progression,recovery=recovery,description=body,source_path=rel,review_status=status))
 candidates={}
 for record in classes:
  path=root/record['source_path']
  for child in path.parent.glob('*.htm'):
   if child!=path and '法术' not in child.stem:candidates[child]=(record,'2024')
 by_name={r['name']:r for r in classes};by_name['邪术师']=by_name['魔契师']
 for book in ('被遗忘的国度','鸦阁魔域：魔障深藏','第三方'):
  for child in (root/book).rglob('*.htm'):
   if '子职' not in '/'.join(child.relative_to(root).parts[:-1]) or '-' not in child.stem:continue
   parent=by_name.get(child.stem.split('-',1)[0])
   if parent:candidates[child]=(parent,'2024' if book!='第三方' else 'unspecified')
 for path,(parent,ruleset) in sorted(candidates.items()):
  rel=path.relative_to(root).as_posix(); parts=rel.split('/');doc=read(path); feats=features(doc)
  heads=doc.xpath('//h1|//h2')
  if not feats or not heads:
   audit.append((rel,'no_explicit_level_features'));continue
  name=bilingual(text(heads[0])); cn,en=re.match(r'^(.*?)(?:\s+([A-Za-z].*))?$',name).groups()
  if not en:audit.append((rel,'no_english_title'))
  sid='subclass-'+digest(rel)
  source=parts[1] if parts[0]=='第三方' else (parts[1] if parts[0]=='被遗忘的国度' else parts[0])
  subclasses.append(dict(id=sid,class_id=parent['id'],name=cn,english_name=en or '',ruleset=ruleset,source=source,source_type=books.get(parts[0],'third_party'),source_path=rel))
  for level,label,body in feats:
   uses,progression,recovery,status=resource(label,body,ruleset,sid)
   subs.append(dict(id='subclass-feature-'+digest(sid+'|'+str(level)+'|'+label),subclass_id=sid,name=label,level=level,uses=uses,uses_by_level=progression,recovery=recovery,description=body,source_path=rel,review_status=status))
 for path in sorted((root/'玩家手册'/'职业').rglob('*.html')):
  audit.append((path.relative_to(root).as_posix(),'legacy_2014_requires_level_mapping'))
 for name,rows in [('classes',classes),('subclasses',subclasses),('class_features',base),('subclass_features',subs)]:
  if not rows or len({r['id'] for r in rows})!=len(rows):raise ValueError('Missing or duplicate '+name)
  with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
  print(name,len(rows))
 with (out/'class-import-review.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['source_path','review_reason']);w.writerows(audit)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('html_root',type=Path);p.add_argument('output_dir',type=Path)
 args=p.parse_args();run(args.html_root,args.output_dir)

