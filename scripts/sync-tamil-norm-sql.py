"""Copy supabase/generated/tamil_norm.sql into the newest migration that carries
BEGIN/END generated markers. Older migrations are already applied in
production and must not change. Run after editing crates/tamil-norm:

    cargo run -q -p tamil-norm --bin tamil-norm-sql > supabase/generated/tamil_norm.sql
    python scripts/sync-tamil-norm-sql.py
"""
import re, glob, os

root = os.path.join(os.path.dirname(__file__), "..")
gen = open(os.path.join(root, "supabase/generated/tamil_norm.sql"), encoding="utf-8").read().strip() + "\n"
paths = sorted(glob.glob(os.path.join(root, "supabase/migrations/*.sql")))
targets = [p for p in paths if "-- BEGIN generated" in open(p, encoding="utf-8").read()]
if not targets:
    raise SystemExit("no migration carries the generated markers")
path = targets[-1]
text = open(path, encoding="utf-8").read()
new = re.sub(
    r"(-- BEGIN generated[^\n]*\n).*?(-- END generated)",
    lambda m: m.group(1) + gen + m.group(2),
    text,
    flags=re.S,
)
if new != text:
    open(path, "w", encoding="utf-8", newline="\n").write(new)
    print("updated", os.path.relpath(path, root))
else:
    print("already current:", os.path.relpath(path, root))
