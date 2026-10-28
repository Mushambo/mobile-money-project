#!/usr/bin/env bash
# Section 3.2  Full offline import into the default 'neo4j' database.
# Neo4j must be STOPPED and the database empty. Run from the project root after
#   python src/prepare_import.py
# Set NEO4J_HOME to your Neo4j Community folder (e.g. ~/neo4j-community-5.26.x).
set -euo pipefail
: "${NEO4J_HOME:?set NEO4J_HOME}"
IMP="${MM_IMPORT_DIR:-$PWD/data/neo4j_import}"

"$NEO4J_HOME/bin/neo4j" stop || true
start=$(date +%s.%N)
"$NEO4J_HOME/bin/neo4j-admin" database import full neo4j \
  --overwrite-destination=true \
  --id-type=integer \
  --nodes=Customer="$IMP/customers.csv" \
  --nodes=Account="$IMP/accounts.csv" \
  --nodes=Device="$IMP/devices.csv" \
  --relationships=OWNS="$IMP/owns.csv" \
  --relationships=USED_DEVICE="$IMP/used_device.csv" \
  --relationships=TRANSFER="$IMP/transfers.csv"
end=$(date +%s.%N)
echo "Import seconds: $(echo "$end - $start" | bc)"
"$NEO4J_HOME/bin/neo4j" start
