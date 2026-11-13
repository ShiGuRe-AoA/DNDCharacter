param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [Parameter(Mandatory=$true)][string]$SqlPath,
  [Parameter(Mandatory=$true)][string]$AuditPath
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$seed = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $root 'rules-migrations/0001_test_spells.sql')
$ddl = [regex]::Match($seed, '(?s)CREATE TABLE(?: IF NOT EXISTS)? spells\s*\(.*?\);').Value
if (!$ddl) { throw 'Missing spells schema in seed file.' }
$legacyIds = @{}
foreach ($m in [regex]::Matches($seed, "\('(?<id>spell-[^']+)', '[^']+', '(?<english>[^']+)', '[^']+', '[^']+', '(?<version>[^']+)', '(?<source>[^']+)'")) {
  $key = @($m.Groups['english'].Value, $m.Groups['version'].Value, $m.Groups['source'].Value) -join '|'
  $legacyIds[$key] = $m.Groups['id'].Value
}
if ($legacyIds.Count -ne 24) { throw 'Expected 24 test spell IDs.' }

$schools = @{
  '防护'='abjuration'; '咒法'='conjuration'; '预言'='divination'; '惑控'='enchantment'
  '塑能'='evocation'; '幻术'='illusion'; '死灵'='necromancy'; '变化'='transmutation'
}
$flags = 'V','S','M','专注','仪式'
$required = @('id','中文名','英文名','环阶_戏法为0','学派','来源作品','来源类型','规则集','可用职业_key',
  '施法时间','施法距离','材料原文','持续时间','完整法术描述','主体效果','升环效果','原始页面路径','锚点','审核状态') + $flags
$rows = @(Import-Csv -LiteralPath $CsvPath -Encoding UTF8)
if (!$rows.Count) { throw 'The CSV has no data rows.' }
foreach ($column in $required) {
  if ($column -cnotin $rows[0].PSObject.Properties.Name) { throw "Missing column: $column" }
}

$utf8 = [Text.UTF8Encoding]::new($false)
$sha = [Security.Cryptography.SHA256]::Create()
$ids = [Collections.Generic.HashSet[string]]::new()
$csvIds = [Collections.Generic.HashSet[string]]::new()
$review = [Collections.Generic.List[object]]::new()
$sql = [Text.StringBuilder]::new()

function SearchKey([string]$value) {
  return ($value.Normalize([Text.NormalizationForm]::FormKC).ToLowerInvariant() -replace '[^\p{L}\p{N}]', '')
}
function SqlText([string]$value) {
  if ($value.Contains([char]0)) { throw 'NUL byte in CSV value.' }
  return "'" + $value.Replace("'", "''") + "'"
}
function AppendSql([string]$statement) {
  if ($utf8.GetByteCount($statement) -gt 95000) { throw 'SQL statement exceeds the import size limit.' }
  [void]$sql.AppendLine($statement)
}
function Upsert($table, $columns, $values, $keep) {
  $assignments = ($columns | Where-Object { $_ -notin $keep } | ForEach-Object { "$_=excluded.$_" }) -join ','
  AppendSql "INSERT INTO $table ($($columns -join ',')) VALUES ($($values -join ',')) ON CONFLICT($($columns[0])) DO UPDATE SET $assignments;"
}

AppendSql ($ddl.Replace('CREATE TABLE spells', 'CREATE TABLE IF NOT EXISTS spells'))
$detailSchema = @'
CREATE TABLE IF NOT EXISTS spell_import_details (
  spell_id TEXT PRIMARY KEY REFERENCES spells(id) ON DELETE CASCADE,
  csv_id TEXT NOT NULL,
  casting_time TEXT NOT NULL,
  casting_range TEXT NOT NULL,
  material_text TEXT NOT NULL,
  class_keys_json TEXT NOT NULL CHECK (json_valid(class_keys_json)),
  full_description TEXT NOT NULL,
  main_effect TEXT NOT NULL,
  upcast_effect TEXT NOT NULL,
  source_path TEXT NOT NULL,
  source_anchor TEXT NOT NULL,
  review_status TEXT NOT NULL
);
'@
AppendSql $detailSchema

$spellColumns = 'id','name','english_name','name_key','english_key','ruleset','source','source_type','level','school',
  'verbal','somatic','material','concentration','ritual','duration','description'
$detailColumns = 'spell_id','csv_id','casting_time','casting_range','material_text','class_keys_json','full_description',
  'main_effect','upcast_effect','source_path','source_anchor','review_status'

foreach ($row in $rows) {
  foreach ($column in 'id','中文名','英文名','来源作品','来源类型','规则集','原始页面路径','审核状态') {
    if ([string]::IsNullOrWhiteSpace($row.$column)) { throw "CSV row $($row.id) is missing $column." }
  }
  if (!$csvIds.Add($row.id)) { throw "Duplicate CSV ID: $($row.id)" }
  if ($row.'环阶_戏法为0' -cnotmatch '^[0-9]$' -or !$schools.ContainsKey($row.学派)) { throw "Invalid level or school: $($row.id)" }
  foreach ($flag in $flags) {
    if ($row.$flag -cnotmatch '^[01]$') { throw "Invalid $flag flag: $($row.id)" }
  }

  $lookup = @($row.英文名, $row.规则集, $row.来源作品) -join '|'
  $spellId = $legacyIds[$lookup]
  if (!$spellId) {
    $identity = ConvertTo-Json -Compress -InputObject @($row.来源作品, $row.规则集,
      (SearchKey $row.英文名), (SearchKey $row.中文名), $row.原始页面路径.Replace('\','/'), $row.锚点)
    $hash = $sha.ComputeHash($utf8.GetBytes($identity))
    $spellId = 'catalog-spell-' + [BitConverter]::ToString($hash).Replace('-','').ToLowerInvariant().Substring(0,24)
  }
  if (!$ids.Add($spellId)) { throw "Duplicate catalog identity at CSV row $($row.id): $spellId" }

  $baseValues = @($spellId, $row.中文名, $row.英文名, (SearchKey $row.中文名), (SearchKey $row.英文名),
    $row.规则集, $row.来源作品, $row.来源类型) | ForEach-Object { SqlText $_ }
  $baseValues = @($baseValues) + @($row.'环阶_戏法为0', (SqlText $schools[$row.学派]), $row.V, $row.S, $row.M,
    $row.专注, $row.仪式, (SqlText $row.持续时间), "''")
  $classes = @($row.可用职业_key -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique)
  $classJson = ConvertTo-Json -Compress -InputObject $classes
  $detailValues = @($spellId, $row.id, $row.施法时间, $row.施法距离, $row.材料原文,
    $classJson, $row.完整法术描述, $row.主体效果, $row.升环效果, $row.原始页面路径,
    $row.锚点, $row.审核状态) | ForEach-Object { SqlText $_ }
  Upsert 'spells' $spellColumns $baseValues @('id','description')
  Upsert 'spell_import_details' $detailColumns $detailValues @('spell_id')

  $reasons = @(
    if ($row.规则集 -eq 'unspecified') { 'ruleset_unspecified' }
    if (!$classes.Count) { 'class_list_missing' }
    if (!$row.锚点) { 'anchor_missing' }
    if ($row.来源类型 -notin 'core','official_supplement','third_party') { 'source_type_review' }
  )
  if ($reasons.Count) {
    $review.Add([pscustomobject]@{ csvId=$row.id; spellId=$spellId; name=$row.中文名; source=$row.来源作品; reasons=$reasons })
  }
}
$sha.Dispose()

$audit = [ordered]@{
  rows = $rows.Count
  stableSeedIdsReused = @($ids | Where-Object { $_ -like 'spell-*' }).Count
  sourceBooks = @($rows | Group-Object 来源作品).Count
  rulesets = @($rows | Group-Object 规则集 | Select-Object Name,Count)
  sourceTypes = @($rows | Group-Object 来源类型 | Select-Object Name,Count)
  reviewStatuses = @($rows | Group-Object 审核状态 | Select-Object Name,Count)
  potentialDuplicates = @($rows | Group-Object 英文名,规则集,来源作品 | Where-Object Count -gt 1 |
    ForEach-Object { [pscustomobject]@{ nameVersionSource=$_.Name; csvIds=@($_.Group.id) } })
  needsReview = $review
}

[IO.File]::WriteAllText($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($SqlPath), $sql.ToString(), $utf8)
[IO.File]::WriteAllText($ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($AuditPath), ($audit | ConvertTo-Json -Depth 8), $utf8)
Write-Output "Generated SQL for $($rows.Count) spells and $($review.Count) audit rows."

