# Section 3.2  Windows PowerShell version of the full offline import.
# Neo4j must be STOPPED and the database empty. Run from the project root after
#   python src\prepare_import.py
# Set $env:NEO4J_HOME to your Neo4j Community folder first.
$ErrorActionPreference = "Stop"
if (-not $env:NEO4J_HOME) { throw "Set `$env:NEO4J_HOME" }
$imp = if ($env:MM_IMPORT_DIR) { $env:MM_IMPORT_DIR } else { Join-Path $PWD "data\neo4j_import" }

& "$env:NEO4J_HOME\bin\neo4j.bat" stop
$sw = [Diagnostics.Stopwatch]::StartNew()
& "$env:NEO4J_HOME\bin\neo4j-admin.bat" database import full neo4j `
  --overwrite-destination=true `
  --id-type=integer `
  "--nodes=Customer=$imp\customers.csv" `
  "--nodes=Account=$imp\accounts.csv" `
  "--nodes=Device=$imp\devices.csv" `
  "--relationships=OWNS=$imp\owns.csv" `
  "--relationships=USED_DEVICE=$imp\used_device.csv" `
  "--relationships=TRANSFER=$imp\transfers.csv"
$sw.Stop()
"Import seconds: {0:N1}" -f $sw.Elapsed.TotalSeconds
& "$env:NEO4J_HOME\bin\neo4j.bat" start
