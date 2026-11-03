"""Build the frozen 462-model authoring IR; never promote it to product profiles."""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,math,re,sys,unicodedata,zipfile
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'development/hardware/selection462'
PLAN=FOLDER/'plan.json'
SELECTION=ROOT/'development/hardware/selected-models-506.json'
# The preparation describes its frozen baseline, not the evolving live coverage.
# Preserve its bytes as profiles are subsequently promoted to the application.
COVERAGE=FOLDER/'coverage-baseline.json'
BASELINE=ROOT/'evidence/s1-20261101/seleccion-462/contrato/BASELINE-406.json'
ARCHIVE=ROOT/'docs/PROYECTOS-REFERENCIA/2026-10-25/archives/netbox-community__devicetype-library__19470a551058.zip'
ARCHIVE_SHA='1821fe01392d088608cf7ab955085ad140a3826bcf91b944d70b99c0dc10e510'
PREFIX='devicetype-library-19470a551058fc9207f036371beefc41b197202e/'
REFERENCES=ROOT/'.local/hardware-visual-500-fe06c3650ef34f5385fdfe813ffcbf7f/REFERENCIAS.json'
REFERENCE_ROOT=REFERENCES.parent
PARSER=ROOT/'.local/catalogo-hardware-69fe34b8842147aebef3757af00d9246/parser'
FIELDS={'interfaces':'interfaces','console-ports':'consolePorts','console-server-ports':'consoleServerPorts','power-ports':'powerPorts','power-outlets':'powerOutlets','front-ports':'frontPorts','rear-ports':'rearPorts','module-bays':'moduleBays','device-bays':'deviceBays','inventory-items':'inventoryItems','port-mappings':'portMappings'}
MOUNTS={'unknown','rackEquipment','desktop','shelf','rackContainer','vertical0U','wall','din'}
def unique_pairs(items):
 result={}
 for k,v in items:
  if k in result:raise ValueError('duplicate_json_key')
  result[k]=v
 return result
def invalid_constant(value):raise ValueError('non_finite_json')
def finite_float(value):
 result=float(value)
 if not math.isfinite(result):raise ValueError('non_finite_json')
 return result
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'),object_pairs_hook=unique_pairs,parse_constant=invalid_constant,parse_float=finite_float)
def pointer(path):return path if path.startswith('/')else'/'+('/'.join(x.replace('~','~0').replace('/','~1')for x in path.split('.')))
def pointed(row,path):
 value=row
 for key in path[1:].split('/'):
  key=key.replace('~1','/').replace('~0','~');value=value[int(key)]if isinstance(value,list)else value[key]
 return value
def pretty(d):return (json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode('utf-8')
def digest(b):return hashlib.sha256(b).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for part in iter(lambda:f.read(1024*1024),b''):h.update(part)
 return h.hexdigest()
def token(s):return ''.join(c for c in unicodedata.normalize('NFKC',s or'').casefold()if c.isalnum()or c=='+')
def brand(s):
 n=token(s);return {'hpearubanetworking':'aruba','hpearuba':'aruba','junipernetworks':'juniper','startechcom':'startech','apcbyschneiderelectric':'apc'}.get(n,n)
def exact(m,c):
 b=brand(c['manufacturer'])
 if b=='hpe'and 'aruba'in token(c['model'])and c.get('partNumber')in{'JL675A','R9Y04A'}:b='aruba'
 return brand(m['manufacturer'])==b and token(m['model'])in{token(c['model']),token(c.get('partNumber'))}
def match_model(m,index,by_path):
 for urls in [m.get('sourcePages',[]),[a.get('sourcePage','')for a in m.get('assets',[])]]:
  paths=[]
  for url in urls:
   hit=re.search(r'/'+re.escape(PREFIX.removeprefix('devicetype-library-').removesuffix('/'))+r'/((?:device|rack)-types/.+\.ya?ml)(?:[?#].*)?$',unquote(url))
   if hit and hit[1]in by_path and exact(m,by_path[hit[1]]):paths.append(hit[1])
  paths=sorted(set(paths))
  if len(paths)==1:return by_path[paths[0]],'original_source_path'
  if len(paths)>1:raise ValueError('ambiguous_original_paths:'+m['id'])
 candidates=[c for c in index if exact(m,c)]
 if len(candidates)>1:raise ValueError('ambiguous_identity:'+m['id'])
 return (candidates[0],'exact_model_or_sku')if candidates else(None,'official_required')

def load_yaml(z,c):
 info=z.getinfo(PREFIX+c['sourcePath'])
 if info.file_size>512*1024:raise ValueError('yaml_size_limit')
 raw=z.read(info)
 if digest(raw)!=c['sourceSha256']:raise ValueError('yaml_hash_mismatch')
 if not PARSER.is_dir():raise ValueError('pinned_yaml_parser_missing')
 if str(PARSER)not in sys.path:sys.path.insert(0,str(PARSER))
 import yaml
 if yaml.__version__!='6.0.3':raise ValueError('pinned_yaml_parser_version_changed')
 if sum(isinstance(e,yaml.events.AliasEvent)for e in yaml.parse(raw))>30:raise ValueError('yaml_alias_limit')
 data=yaml.safe_load(raw)
 if not isinstance(data,dict):raise ValueError('yaml_mapping_required')
 # Plain JSON serialization also rejects recursive structures and unsafe scalars.
 pretty(data)
 return data,raw

def assets_for(m):
 records=[];views={'front':[],'rear':[]}
 for i,a in enumerate(m.get('assets',[]),1):
  rel=a['path'];path=(REFERENCE_ROOT/rel).resolve()
  if not path.is_relative_to(REFERENCE_ROOT.resolve())or not path.is_file()or sha(path)!=a['sha256']:raise ValueError('reference_asset_invalid:'+m['id'])
  identifier='reference-'+str(i);kind='manufacturer_document'if a.get('mediaType')=='application/pdf'else'community_raster'if'community'in a.get('match','')else'manufacturer_raster'
  scope='family'if any(x in a.get('match','')for x in ['family','shared'])else'exact'if a.get('match')in{'exact_model','official_model_reference'}else'unknown'
  record=dict(id=identifier,kind=kind,url=a.get('sourcePage')or a.get('url'),archivePath=None,archiveSha256=None,memberPath=None,memberSha256=None,scope=scope,path=path.relative_to(ROOT).as_posix(),sha256=a['sha256'],view=a.get('view','unknown'),match=a.get('match','unknown'))
  records.append(record)
  if a.get('view')in views:views[a['view']].append(dict(sourceId=identifier,path=record['path'],sha256=a['sha256'],scope=scope))
 return records,views

def dossier(m,c,how,data,official=None):
 refs,views=assets_for(m);sources=[];claims=[];unknown=[]
 dims=dict(width=None,height=None,depth=None);mount=dict(kind='rackContainer'if m['category']=='rack'else'unknown',rackUnits=None,capacityU=None)
 facts=dict(dimensionsMm=dims,mounting=mount,**{v:[]for v in FIELDS.values()})
 identity=dict(manufacturer=m['manufacturer'],model=m['model'],sku=None,hardwareRevision=None)
 def claim(path,source,locator,scope='exact'):claims.append(dict(path=pointer(path),sourceId=source,locator=locator,scope=scope))
 def missing(path,reason,blocks):unknown.append(dict(path=pointer(path),reason=reason,blocks=blocks))
 if c:
  sources.append(dict(id='community-yaml',kind='community_yaml',url=c['sourceUrl'],archivePath=ARCHIVE.relative_to(ROOT).as_posix(),archiveSha256=ARCHIVE_SHA,memberPath=PREFIX+c['sourcePath'],memberSha256=c['sourceSha256'],scope='exact',identityResolution=how))
  identity['sku']=data.get('part_number')or None
  if identity['sku']is not None:claim('identity.sku','community-yaml','/part_number')
  else:missing('identity.sku','not_declared_in_source',['create'])
  u=data.get('u_height')
  if u is not None and(type(u)not in(int,float)or not math.isfinite(u)or u<0):raise ValueError('u_height_invalid')
  if m['category']=='rack':
   mount['capacityU']=u;claim('facts.mounting.capacityU','community-yaml','/u_height')
   if data.get('outer_unit')=='mm':
    for key in dims:
     if data.get('outer_'+key)is not None:dims[key]=data['outer_'+key];claim('facts.dimensionsMm.'+key,'community-yaml','/outer_'+key)
  elif u is not None:
   mount['rackUnits']=u;claim('facts.mounting.rackUnits','community-yaml','/u_height')
   if u>0 and u==int(u):mount['kind']='rackEquipment';claim('facts.mounting.kind','community-yaml','/u_height (declared allocation, not mounting certification)')
   if u==0:missing('facts.mounting.kind','zero_U_does_not_establish_desktop_vertical_wall_or_din',['mount','create'])
   if u!=int(u):missing('facts.mounting.rackUnits','fractional_U_not_supported_by_current_product',['mount','create'])
  for field,out in FIELDS.items():
   if field in data:
    if not isinstance(data[field],list):raise ValueError('component_array_required')
    facts[out]=copy.deepcopy(data[field]);claim('facts.'+out,'community-yaml','/'+field)
   if not data.get(field):missing('facts.'+out,'not_declared_in_source_does_not_mean_physical_zero',['visual','create','cable'])
  if data.get('comments')is not None:
   facts['sourceComments']=copy.deepcopy(data['comments']);claim('facts.sourceComments','community-yaml','/comments')
  if facts['moduleBays']:missing('facts.moduleBays','bay_presence_does_not_establish_installed_modules_or_PSU',['visual','create','cable'])
  def strings(value):
   if isinstance(value,str):yield value
   elif isinstance(value,dict):
    for item in value.values():yield from strings(item)
   elif isinstance(value,list):
    for item in value:yield from strings(item)
  semantic=' '.join(re.sub(r'https?://\S+',' ',s,flags=re.I)for s in strings([facts['interfaces'],data.get('comments','')]))
  if re.search(r'\b(?:combo|shared)\b',semantic,re.I):missing('facts.interfaces','shared_media_requires_explicit_alternatives_not_simultaneous_endpoints',['create','cable'])
  if any(x.get('type')=='other'for x in facts['interfaces']):missing('facts.interfaces','other_is_not_a_verified_connector_form_or_protocol',['visual','create','cable'])
 if official:
  facts['officialDeclarations']={k:copy.deepcopy(official.get(k,[]))for k in ['documentedInterfaces','documentedPower']}
  records=official.get('sourceRecords',[])
  for i,s in enumerate(records,1):
   if s.get('path'):
    p=(ROOT/s['path']).resolve()
    if not p.is_relative_to(ROOT.resolve())or not p.is_file()or sha(p)!=s.get('sha256'):raise ValueError('official_document_hash_invalid')
   else:missing('sourceRecords','official_web_only_source_not_reproducible_offline',['visual','create','cable','mount'])
   sources.append(dict(id='official-'+str(i),kind='manufacturer_document',url=s.get('url'),archivePath=None,archiveSha256=None,memberPath=None,memberSha256=None,scope=s.get('scope','unknown'),details=s))
  def official_fact(path,entry=None):
   candidates=[(i,s,max([len(p)for p in s.get('factPaths',[])if path==p or path.startswith(p+'.')],default=0))for i,s in enumerate(records)]
   longest=max([size for i,s,size in candidates],default=0);candidates=[(i,s)for i,s,size in candidates if size==longest and size>0]
   if len(candidates)>1 and isinstance(entry,dict)and type(entry.get('sourceRecord'))is int:candidates=[(i,s)for i,s in candidates if i==entry['sourceRecord']]
   if len(candidates)!=1 or not candidates[0][1].get('locator'):
    target='facts.officialDeclarations.'+path if path.startswith('documented')else'facts.officialNotes'+path.removeprefix('notes')if path.startswith('notes')else'identity.sku'if path=='sku'else'facts.'+path
    missing(target,'official_fact_source_missing_or_ambiguous',['visual','create','cable','mount']);return None
   i,s=candidates[0];return('official-'+str(i+1),entry.get('locator')if isinstance(entry,dict)and entry.get('sourceRecord')==i and entry.get('locator')else s['locator'],s.get('scope','unknown'))
  if official.get('sku')is not None:
   origin=official_fact('sku')
   if origin:identity['sku']=official['sku'];claim('identity.sku',*origin)
  for key,val in official.get('dimensionsMm',{}).items():
   if key in dims and val is not None:
    origin=official_fact('dimensionsMm.'+key)
    if origin:dims[key]=val;claim('facts.dimensionsMm.'+key,*origin)
  for key,val in official.get('mounting',{}).items():
   if key in mount and val is not None:
    origin=official_fact('mounting.'+key)
    if origin:mount[key]=val;claim('facts.mounting.'+key,*origin)
  facts['officialNotes']=official.get('notes',[])
  def official_leaves(value,source_path,target_path,context=None):
   if isinstance(value,dict):
    for k,v in value.items():
     if k not in{'sourceRecord','locator'}:official_leaves(v,source_path+'.'+k,target_path+'/'+k.replace('~','~0').replace('/','~1'),value)
   elif isinstance(value,list):
    for i,v in enumerate(value):official_leaves(v,source_path+'.'+str(i),target_path+'/'+str(i),context)
   else:
    if value is None:
     missing(target_path,'not_declared_by_official_source',['visual','create','cable','mount']);return
    origin=official_fact(source_path,context)
    if origin:claim(target_path,*origin)
  for name,items in facts['officialDeclarations'].items():official_leaves(items,name,'/facts/officialDeclarations/'+name)
  official_leaves(facts['officialNotes'],'notes','/facts/officialNotes')
  for item in official.get('unknowns',[]):
   original=item.get('path','')if isinstance(item,dict)else'';reason=item.get('reason','not_declared_by_official_source')if isinstance(item,dict)else str(item)
   target='identity.'+original if original=='sku'else'facts.officialDeclarations.'+original if original.startswith('documented')else'facts.officialNotes'+original.removeprefix('notes')if original.startswith('notes')else'facts.'+original if original.startswith(('dimensionsMm','mounting'))else'facts.officialDeclarations'
   missing(target,reason,['visual','create','cable','mount'])
 if not c:missing('facts','no_exact_community_yaml',['visual','create','cable','mount'])
 sources+=refs
 for key,val in dims.items():
  if val is None:missing('facts.dimensionsMm.'+key,'no_verified_complete_dimension',['visual','mount','create'])
 for side in ['front','rear']:missing('visual.'+side+'.geometry','no_verified_connector_to_geometry_mapping',['visual','create','cable'])
 row=dict(selectionId=m['id'],identity=identity,category=m['category'],sourceRecords=sources,facts=facts,visual={side:dict(referenceAssets=views[side],geometry=None,status='reference_only'if views[side]else'unknown')for side in views},claims=claims,unknowns=unknown,capabilities=dict(visual='reference_only',create='blocked',cable='blocked',mount='blocked'),promotion=dict(status='not_submitted',profileKey=None,profileRevision=None,blockers=sorted({u['reason']for u in unknown})))
 validate_row(row)
 return row

def validate_row(row):
 if set(row)!={'selectionId','identity','category','sourceRecords','facts','visual','claims','unknowns','capabilities','promotion'}:raise ValueError('row_fields_invalid')
 if set(row['identity'])!={'manufacturer','model','sku','hardwareRevision'}:raise ValueError('identity_fields_invalid')
 if set(row['capabilities'])!={'visual','create','cable','mount'}or set(row['promotion'])!={'status','profileKey','profileRevision','blockers'}:raise ValueError('state_fields_invalid')
 required={'dimensionsMm','mounting',*FIELDS.values()}
 if not required<=set(row['facts'])<=required|{'officialDeclarations','officialNotes','sourceComments'}:raise ValueError('fact_fields_invalid')
 if set(row['facts']['dimensionsMm'])!={'width','height','depth'}or set(row['facts']['mounting'])!={'kind','rackUnits','capacityU'}:raise ValueError('dimension_mount_fields_invalid')
 if set(row['visual'])!={'front','rear'}or any(set(v)!={'referenceAssets','geometry','status'}for v in row['visual'].values()):raise ValueError('visual_fields_invalid')
 for field in FIELDS.values():
  if not isinstance(row['facts'][field],list)or any(not isinstance(x,dict)for x in row['facts'][field]):raise ValueError('component_record_invalid')
 mount=row['facts']['mounting']
 for key in ['rackUnits','capacityU']:
  val=mount[key]
  if val is not None and(type(val)not in(int,float)or not math.isfinite(val)or val<0):raise ValueError('mount_quantity_invalid')
 if mount['kind']=='rackEquipment'and mount['rackUnits']is not None and(mount['rackUnits']<=0 or mount['rackUnits']!=int(mount['rackUnits'])):raise ValueError('rack_allocation_invalid')
 if row['capabilities']['visual']not in{'unknown','reference_only'}:raise ValueError('unreviewed_visual_claim')
 if row['promotion']['status']!='not_submitted'or any(row['capabilities'][k]!='blocked'for k in ['create','cable','mount']):raise ValueError('unreviewed_profile_cannot_be_promoted')
 if row['promotion']['profileKey']is not None or row['promotion']['profileRevision']is not None:raise ValueError('promotion_identity_must_be_empty')
 if any(row['visual'][s]['geometry']is not None for s in ['front','rear']):raise ValueError('geometry_not_part_of_reference_extraction')
 if row['facts']['mounting']['kind']not in MOUNTS:raise ValueError('mount_kind_invalid')
 if row['category']=='rack'and(row['facts']['mounting']['kind']!='rackContainer'or row['facts']['mounting']['rackUnits']is not None):raise ValueError('rack_container_cannot_be_rack_equipment')
 ids={s['id']for s in row['sourceRecords']}
 if len(ids)!=len(row['sourceRecords'])or any(c['sourceId']not in ids for c in row['claims']):raise ValueError('claim_source_invalid')
 sources={s['id']:s for s in row['sourceRecords']};levels={'unknown':0,'family':1,'exact':2}
 for s in row['sourceRecords']:
  if s['kind']not in{'community_yaml','manufacturer_document','community_raster','manufacturer_raster','own_geometry','execution_evidence','generated_manifest'}or s['scope']not in levels:raise ValueError('source_contract_invalid')
  if s.get('url')is not None and(not isinstance(s['url'],str)or not s['url'].startswith('https://')):raise ValueError('source_url_invalid')
  for key in ['archiveSha256','memberSha256','sha256']:
   if s.get(key)is not None and not re.fullmatch('[0-9a-f]{64}',s[key]):raise ValueError('source_hash_invalid')
 for c in row['claims']:
  if set(c)!={'path','sourceId','locator','scope'}:raise ValueError('claim_fields_invalid')
  if not isinstance(c['path'],str)or not c['path'].startswith('/')or re.search(r'~(?![01])',c['path']):raise ValueError('claim_pointer_invalid')
  try:pointed(row,c['path'])
  except(KeyError,IndexError,TypeError,ValueError):raise ValueError('claim_path_missing')
  if c['scope']not in levels or levels[c['scope']]>levels[sources[c['sourceId']]['scope']]:raise ValueError('claim_scope_escalation')
  if not isinstance(c['locator'],str)or not c['locator']:raise ValueError('claim_locator_missing')
 for side,v in row['visual'].items():
  if side not in{'front','rear'}or v['status']not in{'unknown','reference_only'}:raise ValueError('visual_state_invalid')
  for a in v['referenceAssets']:
   if not isinstance(a,dict)or set(a)!={'sourceId','path','sha256','scope'}or a['sourceId']not in sources:raise ValueError('reference_contract_invalid')
   s=sources[a['sourceId']]
   if any(a[k]!=s[k]for k in ['path','sha256','scope']):raise ValueError('reference_source_mismatch')
 for u in row['unknowns']:
  if set(u)!={'path','reason','blocks'}or not isinstance(u['path'],str)or not u['path'].startswith('/')or not u['reason']or not u['blocks']or not set(u['blocks'])<={'visual','create','cable','mount'}:raise ValueError('unknown_contract_invalid')
 for val in row['facts']['dimensionsMm'].values():
  if val is not None and(type(val)not in(int,float)or not math.isfinite(val)or val<=0):raise ValueError('dimension_invalid')
 if not row['unknowns']or not row['promotion']['blockers']:raise ValueError('unknowns_cannot_be_erased')

def build(require_official=False):
 selected=read(SELECTION);coverage=read(COVERAGE);pending=sorted(x['id']for x in coverage['rows']if not x['profileKey'])
 if len(pending)!=462:raise ValueError('frozen_462_baseline_required')
 plan=dict(formatVersion=1,batchId='selected-462-20261101-v1',selectionSha256=sha(SELECTION),coverageBaselineSha256=sha(COVERAGE),baseline406Sha256=sha(BASELINE),selectionIds=pending,archiveSha256=ARCHIVE_SHA)
 if PLAN.exists()and read(PLAN)!=plan:raise ValueError('preparation_plan_changed_requires_separate_revision')
 if sha(ARCHIVE)!=ARCHIVE_SHA:raise ValueError('archive_hash_mismatch')
 index=read(ROOT/'docs/CATALOGO-HARDWARE-REFERENCIA/MODELOS-COMUNIDAD.json')['models']+read(ROOT/'docs/CATALOGO-HARDWARE-REFERENCIA/MODELOS-RACKS.json')['models'];by_path={m['sourcePath']:m for m in index}
 originals={m['id']:m for m in read(REFERENCES)['models']};official_rows=read(FOLDER/'official.json')['models']if require_official and(FOLDER/'official.json').exists()else[]
 official={m['selectionId']:m for m in official_rows}
 if len(official)!=len(official_rows):raise ValueError('duplicate_official_identity')
 for key,m in official.items():
  if key not in pending or brand(m['manufacturer'])!=brand(originals[key]['manufacturer'])or token(m['model'])!=token(originals[key]['model']):raise ValueError('official_model_substitution')
 if require_official and len(official)!=11:raise ValueError('eleven_official_records_required')
 rows=[];matches=[]
 with zipfile.ZipFile(ARCHIVE)as z:
  for identifier in pending:
   m=originals[identifier];c,how=match_model(m,index,by_path);data,raw=load_yaml(z,c)if c else(None,None)
   rows.append(dossier(m,c,how,data,official.get(identifier)))
   matches.append(dict(selectionId=identifier,sourcePath=c['sourcePath']if c else None,resolution=how,sourceSha256=c['sourceSha256']if c else None))
 if sum(x['sourcePath']is not None for x in matches)!=451:raise ValueError('expected_451_exact_yaml_matches')
 if require_official and set(official)!={x['selectionId']for x in matches if x['sourcePath']is None}:raise ValueError('official_set_must_match_eleven_yaml_gaps')
 files={PLAN:pretty(plan),FOLDER/'source-matches.json':pretty(dict(formatVersion=1,archiveSha256=ARCHIVE_SHA,models=matches))}
 for i in range(3):files[FOLDER/f'part-{i+1:02}.json']=pretty(dict(**{k:v for k,v in plan.items()if k not in['selectionIds','archiveSha256']},part=dict(index=i+1,count=3),models=rows[154*i:154*(i+1)]))
 stats=dict(models=462,parts=3,exactCommunityYaml=451,officialRecords=len(official),geometryComplete=0,promotedProfiles=0,existingCommercialProfiles=406,existingSelectedCoverage=44,selectedProfilesStillPending=462,archiveSha256=ARCHIVE_SHA)
 input_files=[SELECTION,COVERAGE,BASELINE,REFERENCES,Path(__file__).resolve(),ROOT/'docs/CATALOGO-HARDWARE-REFERENCIA/MODELOS-COMUNIDAD.json',ROOT/'docs/CATALOGO-HARDWARE-REFERENCIA/MODELOS-RACKS.json']
 if require_official:input_files.append(FOLDER/'official.json')
 files[FOLDER/'manifest.json']=pretty(dict(formatVersion=1,state='authoring_reference_IR_not_product_profiles',counts=stats,files={p.relative_to(ROOT).as_posix():digest(b)for p,b in files.items()},inputs={p.relative_to(ROOT).as_posix():sha(p)for p in input_files}))
 return files,stats

def main():
 p=argparse.ArgumentParser(description=__doc__);a=p.add_mutually_exclusive_group(required=True);a.add_argument('--write',action='store_true');a.add_argument('--check',action='store_true');p.add_argument('--require-official',action='store_true');a=p.parse_args();files,stats=build(a.require_official)
 for path,data in files.items():
  if a.write:path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  else:
   if not path.is_file()or path.read_bytes()!=data:raise ValueError('selected_preparation_stale:'+path.name)
 print(json.dumps(dict(result='written'if a.write else'checked',**stats,writesProduct=False,writesLedger=False)))
if __name__=='__main__':main()
