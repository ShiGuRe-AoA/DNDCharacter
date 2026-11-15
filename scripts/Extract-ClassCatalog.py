import argparse,csv,hashlib,re
from pathlib import Path
from collections import Counter, defaultdict
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
def legacy_subclass_markers(doc):
 levels={}
 for table in doc.xpath('//table'):
  rows=table.xpath('.//tr')
  if not rows:continue
  header=[text(cell) for cell in rows[0].xpath('./td|./th')]
  if len(header)<2 or '等级' not in header[0] or '特性' not in header[1]:continue
  for row in rows[1:]:
   cells=[text(cell) for cell in row.xpath('./td|./th')]
   if len(cells)<2:continue
   match=re.fullmatch(r'(\d{1,2})(?:st|nd|rd|th|级)?',cells[0],re.I)
   if match:
    for name in re.split(r'[，、；]',cells[1]):
     levels[norm(name)]=int(match[1])
 markers={}
 for label in doc.xpath('//em | //i'):
  match=re.fullmatch(r'第?\s*(\d{1,2})\s*级.{1,55}特性[。.]?',text(label))
  extra_label=None
  if not match and text(label)=='特性':
   previous=label.getprevious()
   if previous is not None:
    match=re.fullmatch(r'第?\s*(\d{1,2})\s*级.{1,55}特性',text(previous)+text(label))
    if match:extra_label=previous
  if not match:continue
  heading=(extra_label if extra_label is not None else label).getprevious()
  while heading is not None and (heading.tag=='br' or not text(heading)):
   heading=heading.getprevious()
  if heading is not None and heading.tag in ('font','strong','b','span'):
   name=bilingual(text(heading))
   if name and len(name)<=100:
    markers[heading]=(None,int(match[1]),name)
    markers[label]=None
    if extra_label is not None:markers[extra_label]=None
 for heading in doc.xpath('//strong | //b | //h3 | //h4 | //h5'):
  if any(el in heading.iterancestors() or heading in el.iterancestors() for el in markers):continue
  name=bilingual(text(heading))
  chinese=re.split(r'\s+(?=[A-Za-z])',name,maxsplit=1)[0]
  if chinese in levels and chinese!=name and heading.getparent().tag not in ('td','th'):
   markers[heading]=(None,levels[chinese],name)
 return markers

def features(doc,legacy=False):
 markers=[]
 for element in doc.xpath('//font[@color] | //h3 | //h4 | //h5 | //strong | //u | //b | //span'):
  if element.tag=='font' and element.get('color','').lower() not in ('#800000','#d08c36'): continue
  match=LEVEL.fullmatch(text(element))
  if not match or not 1<=int(match[1])<=20 or len(match[2])>100: continue
  if any(element in el.iterancestors() or el in element.iterancestors() for el,_ in markers):continue
  markers.append((element,match))
 markers={element:match for element,match in markers}
 if not markers and legacy:markers=legacy_subclass_markers(doc)
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
   if markers[el] is None:return
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

def quick_reference(root):
 toc=read(root/'DND五版不全书.hhc')
 sections=toc.xpath('//li[object/param[@name="Name" and @value="本书速查"]]/ul/li[object/param[@name="Name" and @value="职业速查"]]')
 if len(sections)!=1:raise ValueError('Expected one 本书速查 → 职业速查 section')
 def value(node,name):
  return next(iter(node.xpath(f'./object/param[@name="{name}"]/@value')),'')
 for group in sections[0].xpath('./ul/li[ul]'):
  page=value(group,'Local')
  if not page:continue
  links={}
  for node in group.xpath('./ul/li'):
   name=value(node,'Name'); target=value(node,'Local')
   if (not target or name.startswith('—') or target.startswith('速查/') or
       name in ('超魔法选项','禁令恩惠选项','战技选项','血咒','血族专长') or
       name.startswith(('魔能祈唤选项','大招变体'))):continue
   links[root/target]=re.sub(r'（[^）]+）$','',name)
  yield value(group,'Name'),root/page,links

def quick_ruleset(relative):
 if relative.parts[0] in ('玩家手册2024','艾伯伦：奇械锻炉','被遗忘的国度','鸦阁魔域：魔障深藏'):return '2024'
 if relative.parts[0] in ('第三方','其他','奥术之书','奥术奥秘'):return 'unspecified'
 return '2014'

# These layouts have reviewed bilingual headers and prose unlock levels.
REVIEWED_UNLOCKS={
 '游荡者-残戮行医': {'Medic':3,'Transfusion':3,'Field Surgeon':9,'Toxic Shock':13,'Bloodbound':17},
 '德鲁伊-落英结社': {'Petal Dance':2,'Petal Beast Mimicry':6,'Spirit of Obojima':10,'Winds of Revival':14},
 '术士-鬼之血脉': {'Arcane Prison':1,'Oni Traits':1,'Ogre Manipulation':6,'Boiling Power':14,'Transformation':18},
 '化狼结社': {'Heightened Senses':3,'Hybrid Transformation':3,"Stalker's Prowess":7,
   'Advanced Transformation':11,'Brand of the Voracious':15,'Hybrid Transformation Mastery':18},
 '弑灵结社': {'Rite of the Dawn':3,'Curse Specialist':3,'Ethereal Step':7,
   'Brand of Sundering':11,'Blood Curse of the Exorcist':15,'Rite Revival':18},
 '渎魂结社': {'Otherworldly Patron':3,'Pact Magic':3,'Rite Focus':3,'Mystic Frenzy':7,
   'Revealed Arcana':7,'Brand of the Sapping Scar':11,'Unsealed Arcana':15},
 '突变结社': {'Mutagencraft':3,'Strange Metabolism':7,'Brand of Axiom':11,
   'Blood Curse of Corrosion':15,'Exalted Mutation':18}
}

def infer_subclass_features(doc,profiles,subclass_name,reviewed=None):
 # Colored bilingual headings delimit features in several older book layouts.
 patterns=Counter(tuple(profile) for profile in profiles if profile)
 if not patterns and not reviewed:return []
 candidates=[]
 selector='//body//font[@color] | //body//h3 | //body//h4 | //body//h5'
 if reviewed:selector+=' | //body//strong | //body//b'
 for node in doc.xpath(selector):
  if node.xpath('ancestor::h1 | ancestor::h2 | ancestor::li'):continue
  if not reviewed and node.xpath('ancestor::table'):continue
  label=bilingual(text(node))
  match=re.fullmatch(r'([\u3400-\u9fff][^。！？\n]{0,30}?)\s+([A-Za-z][A-Za-z0-9 ,\'’&()\-:]{1,65})',label)
  if not match or match[1]==subclass_name or match[2].endswith(('Options','Spells Table')):continue
  if reviewed and match[2] not in reviewed:continue
  if any(old in node.iterancestors() for old in candidates):continue
  candidates.append(node)
 if not candidates:return []
 chunks=[]; rows=[]; heading=None
 def flush():
  if heading is None:return
  body='\n'.join(norm(line) for line in ''.join(chunks).splitlines() if norm(line))
  if body:rows.append((bilingual(text(heading)),body))
 def walk(node):
  nonlocal heading,chunks
  if node in headings:
   flush();heading=node;chunks=[];return
  if not isinstance(node.tag,str) or node.tag in ('script','style','nav'):return
  if heading is not None:
   if node.tag in ('br','p','li','tr','div'):chunks.append('\n')
   if node.text:chunks.append(node.text)
  for child in node:
   walk(child)
   if heading is not None and child.tail:chunks.append(child.tail)
 headings=set(candidates)
 walk(doc);flush()
 if not rows:return []
 if reviewed:
  return [(reviewed[re.split(r'\s+(?=[A-Za-z])',name,maxsplit=1)[1]],name,body) for name,body in rows]
 count=len(rows)
 explicit=[]
 for _,body in rows:
  lead=norm(body)
  match=re.match(r'^(?:同样|此外)?[，, ]*(?:当你(?:达到|到达|升至|升到)?|在|从|自|达到|到达)?\s*第?\s*(\d{1,2})\s*级(?:起|时|后|开始|加入|的|[，：])',lead)
  explicit.append(int(match[1]) if match else None)
 possible=[profile for profile in patterns if len(profile)==count and all(given is None or given==level for given,level in zip(explicit,profile))]
 if not possible:
  return [(level,name,body) for level,(name,body) in zip(explicit,rows) if level and any(level in profile for profile in patterns)]
 ranked=sorted(possible,key=lambda profile:(-patterns[profile],profile))
 if len(ranked)>1 and patterns[ranked[0]]==patterns[ranked[1]]:
  return [(level,name,body) for level,(name,body) in zip(explicit,rows) if level and any(level in profile for profile in patterns)]
 return [(level,name,body) for level,(name,body) in zip(ranked[0],rows)]

def run(root,out):
 out.mkdir(parents=True,exist_ok=True)
 classes=[];subclasses=[];base=[];subs=[];audit=[]
 books={'玩家手册':'core','塔莎的万事坩埚':'official_supplement','珊娜萨的万事指南':'official_supplement','荒洲探险家指南':'official_supplement','拉尼卡公会长指南':'official_supplement','玩家手册2024':'core','艾伯伦：奇械锻炉':'official_supplement','被遗忘的国度':'official_supplement','鸦阁魔域：魔障深藏':'official_supplement'}
 for cn,(cid,en,die,ability) in CLASS.items():
  path=root/'玩家手册2024'/'角色职业'/cn/(cn+'.htm')
  if cid=='artificer':path=root/'艾伯伦：奇械锻炉'/'第一章'/'奇械师.htm'
  if not path.exists():raise ValueError(path)
  rel=path.relative_to(root).as_posix(); book=rel.split('/')[0]
  classes.append(dict(id=cid,name=cn,english_name=en,ruleset='2024',source=book,source_type=books[book],hit_die=die,casting_ability=ability,source_path=rel))
  for level,name,body in features(read(path)):
   uses,progression,recovery,status=resource(name,body,'2024',cid)
   base.append(dict(id='class-feature-'+digest(cid+'|'+str(level)+'|'+name),class_id=cid,name=name,level=level,uses=uses,uses_by_level=progression,recovery=recovery,description=body,source_path=rel,review_status=status))
 indexed={}
 third_party={
  '血猎手':('bloodhunter','Blood Hunter',10),'邪狱使':('illrigger','Illrigger',10),
  '铳士（尖塔）':('gunslinger','Gunslinger',8),'怪物猎人（鬼魅幽谷）':('monsterhunter','Monster Hunter',10),
  '拳斗士':('pugilist','Pugilist',10),'血族（吸血鬼）':('kindred','Kindred',10)
 }
 for name,path,links in quick_reference(root):
  class_name=re.sub(r'（[^）]+）$','',name)
  parent=next((record for record in classes if record['name']==class_name),None)
  if parent is None:
   cid,en,die=third_party[name]
   rel=path.relative_to(root)
   parent=dict(id=cid,name=class_name,english_name=en,ruleset='unspecified',source=rel.parts[1],source_type='third_party',hit_die=die,casting_ability='',source_path=rel.as_posix())
   classes.append(parent)
   parsed=features(read(path),legacy=True)
   if not parsed:audit.append((rel.as_posix(),'class_features_need_review'))
   for level,label,body in parsed:
    uses,progression,recovery,status=resource(label,body,'unspecified',cid)
    base.append(dict(id='class-feature-'+digest(cid+'|'+str(level)+'|'+label),class_id=cid,name=label,level=level,uses=uses,uses_by_level=progression,recovery=recovery,description=body,source_path=rel.as_posix(),review_status=status))
  for child,label in links.items():
   indexed[child]=(parent,label)
 candidates={}
 for record in classes:
  if record['source_type']=='third_party':continue
  path=root/record['source_path']
  for child in path.parent.glob('*.htm'):
   if child!=path and '法术' not in child.stem:candidates[child]=(record,'2024')
 by_name={r['name']:r for r in classes};by_name['邪术师']=by_name['魔契师']
 for book in ('被遗忘的国度','鸦阁魔域：魔障深藏','第三方'):
  for child in (root/book).rglob('*.htm'):
   if '子职' not in '/'.join(child.relative_to(root).parts[:-1]) or '-' not in child.stem:continue
   parent=by_name.get(child.stem.split('-',1)[0])
   if parent:candidates[child]=(parent,'2024' if book!='第三方' else 'unspecified')
 # Legacy books organize subclass pages below a class folder; TCE uses a (TCE) suffix.
 for book,parts in {
  '塔莎的万事坩埚':('玩家选项','职业'),
  '珊娜萨的万事指南':('角色选项',),
  '玩家手册':('职业',)
 }.items():
  for folder in (root/book).joinpath(*parts).iterdir():
   parent=by_name.get(re.sub(r'[（(]TCE[）)]$','',folder.name))
   if not folder.is_dir() or not parent:continue
   for child in folder.iterdir():
    if child.is_file() and child.suffix.lower() in ('.htm','.html'):candidates[child]=(parent,'2014')
 for book in ('荒洲探险家指南','拉尼卡公会长指南'):
  for child in (root/book).rglob('*.htm'):
   parent=by_name.get(re.split(r'[-·]',child.stem,maxsplit=1)[0])
   if parent and re.search(r'[-·]',child.stem):candidates[child]=(parent,'2014')
 for child,(parent,label) in indexed.items():
  _,ruleset=candidates.get(child,(parent,quick_ruleset(child.relative_to(root))))
  candidates[child]=(parent,ruleset)
 profiles=defaultdict(list)
 parsed_pages={}
 for path,(parent,ruleset) in candidates.items():
  parsed=features(read(path),ruleset!='2024')
  parsed_pages[path]=parsed
  if parsed:
   profiles[parent['id'],ruleset].append(sorted(level for level,_ in {(level,label) for level,label,_ in parsed}))
 for path,(parent,ruleset) in sorted(candidates.items()):
  rel=path.relative_to(root).as_posix(); parts=rel.split('/');doc=read(path); feats=parsed_pages[path]
  inferred=False
  heads=doc.xpath('//h1|//h2')
  if ruleset=='2014' and (not heads or parts[0]=='玩家手册'):
   title=re.split(r'[-·]',path.stem)[-1]
   heads=[node for node in doc.xpath('//body/p | //body/h2 | //body/strong') if len(text(node))<=90 and (text(node).startswith(title) or (parts[0]=='珊娜萨的万事指南' and re.search(r'[A-Za-z]',text(node))))]
  if not feats:
   if path not in indexed:
    audit.append((rel,'no_explicit_level_features'));continue
   cid=parent['id']
   reference=profiles[cid,ruleset]
   if not reference or ruleset=='unspecified':
    reference=[*reference,*profiles[cid,'2014'],*profiles[cid,'2024']]
   feats=infer_subclass_features(doc,reference,indexed[path][1],REVIEWED_UNLOCKS.get(path.stem))
   inferred=bool(feats)
   audit.append((rel,'inferred_levels_review' if inferred else 'no_explicit_level_features'))
  if not heads and path not in indexed:
   audit.append((rel,'no_subclass_title'));continue
  fallback=indexed[path][1] if path in indexed else path.stem
  name=bilingual(text(heads[0])) if heads else fallback
  cn,en=re.match(r'^(.*?)(?:\s+([A-Za-z].*))?$',name).groups()
  if path in indexed and not en:cn=fallback
  if not en:audit.append((rel,'no_english_title'))
  sid='subclass-'+digest(rel)
  source=parts[1] if parts[0]=='第三方' else (parts[1] if parts[0]=='被遗忘的国度' else parts[0])
  subclasses.append(dict(id=sid,class_id=parent['id'],name=cn,english_name=en or '',ruleset=ruleset,source=source,source_type=books.get(parts[0],'third_party' if parts[0]=='第三方' else 'official_supplement'),source_path=rel))
  grouped={}
  for level,label,body in feats:
   texts=grouped.setdefault((level,label),[])
   if body not in texts:texts.append(body)
  for (level,label),texts in grouped.items():
   if len(texts)>1:audit.append((rel,'repeated_feature_heading'))
   body='\n\n'.join(texts)
   uses,progression,recovery,status=resource(label,body,ruleset,sid)
   if inferred:status='inferred_level:'+status
   subs.append(dict(id='subclass-feature-'+digest(sid+'|'+str(level)+'|'+label),subclass_id=sid,name=label,level=level,uses=uses,uses_by_level=progression,recovery=recovery,description=body,source_path=rel,review_status=status))
 for path in sorted((root/'玩家手册'/'职业').rglob('*.html')):
  if path not in candidates:audit.append((path.relative_to(root).as_posix(),'legacy_2014_requires_level_mapping'))
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

