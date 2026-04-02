import re

with open("apps/api/src/cashflow_os/db/repository.py", "r") as f:
    code = f.read()

# Make it SQLite compatible
code = code.replace("PostgresRepository", "SQLiteRepository")
code = code.replace("cashflow.", "")
code = code.replace("now()", "CURRENT_TIMESTAMP")
code = code.replace("::jsonb", "")
code = code.replace("::json", "")

# Replace gen_random_uuid()::text with python generated uuids.
# There are two places: bank_balance_snapshots and inventory_snapshots
# Both use (gen_random_uuid()::text, :org_id...)
import uuid

# We will just inject it in the parameters.
# Wait, replacing them dynamically using python is easier!
code = code.replace("gen_random_uuid()::text", ":snapshot_id")
code = code.replace("gen_random_uuid()", ":snapshot_id")

with open("apps/api/src/cashflow_os/db/repository.py", "w") as f:
    f.write(code)
