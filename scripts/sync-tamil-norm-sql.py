"""Copy supabase/generated/tamil_norm.sql into the migration that defines the
function, between the BEGIN/END generated markers. Run after changing
crates/tamil-norm and regenerating the SQL:

    cargo run -q -p tamil-norm --bin tamil-norm-sql > supabase/generated/tamil_norm.sql
    python scripts/sync-tamil-norm-sql.py
"""
import re, sys, glob, os

root = os.path.join(os.path.dirname(__file__), "..")
gen = open(os.path.join(root, "supabase/generated/tamil_norm.sql"), encoding="utf-8").read().strip() + "\n"
changed = 0
for path in glob.glob(os.path.join(root, "supabase/migrations/*.sql")):
    text = open(path, encoding="utf-8").read()
    new = re.sub(
        r"(-- BEGIN generated[^\n]*\n).*?(-- END generated)",
        lambda m: m.group(1) + gen + m.group(2),
        text,
        flags=re.S,
    )
    if new != text:
        open(path, "w", encoding="utf-8", newline="\n").write(new)
        changed += 1
        print("updated", os.path.relpath(path, root))
print("files changed:", changed)
