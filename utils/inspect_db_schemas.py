from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
conn = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
schemas = [r[0] for r in conn.execute('SELECT schema_name FROM information_schema.schemata').fetchall()]
print("Available Schemas in DuckDB:", schemas)

for s in ['bronze', 'main_silver', 'main_gold', 'raw']:
    if s in schemas:
        tables = [r[0] for r in conn.execute(f"SELECT table_name FROM information_schema.tables WHERE table_schema='{s}'").fetchall()]
        print(f"\nSchema [{s}] ({len(tables)} objects):")
        for t in tables:
            cnt = conn.execute(f"SELECT COUNT(*) FROM {s}.{t}").fetchone()[0]
            print(f"   * {t:<32} -> {cnt} rows")

conn.close()
