import csv,sys
from pathlib import Path
root=Path(sys.argv[1])
schema=Path(sys.argv[2]).read_text(encoding='utf-8-sig')
def literal(value):
 return "'"+value.replace("'","''")+"'"
with (root/'class-catalog-import.sql').open('w',encoding='utf-8') as out:
 out.write(schema+'\n')
 for name in ('classes','subclasses','class_features','subclass_features'):
  for row in csv.DictReader((root/(name+'.csv')).open(encoding='utf-8-sig',newline='')):
   fields=','.join(row)
   values=','.join(row[k] if k in ('level','hit_die') else literal(row[k]) for k in row)
   updates=','.join(f'{key}=excluded.{key}' for key in row if key!='id')
   out.write(f'INSERT INTO rules_{name} ({fields}) VALUES ({values}) ON CONFLICT(id) DO UPDATE SET {updates};\n')

