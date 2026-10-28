"""Section 1.1 - record software/driver versions, hardware, OS and database memory settings,
and prove both connections work.   python src/workspace_info.py [--engines pg neo]"""
import argparse
import json
import platform
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import RESULTS_DIR  # noqa: E402
from db import run_neo, run_pg  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--engines", nargs="+", default=["pg", "neo"])
    a = ap.parse_args()
    info = {"recorded_at_cat": datetime.now(ZoneInfo("Africa/Kigali")).isoformat(timespec="seconds"),
            "os": platform.platform(), "python": sys.version.split()[0], "cpu": platform.processor() or platform.machine()}
    try:
        import psutil
        info["logical_cpus"] = psutil.cpu_count()
        info["physical_cpus"] = psutil.cpu_count(logical=False)
        info["ram_gb"] = round(psutil.virtual_memory().total / 1e9, 2)
    except ImportError:
        import os
        info["logical_cpus"] = os.cpu_count()
    import numpy
    info["numpy"] = numpy.__version__
    if "pg" in a.engines:
        import psycopg
        info["psycopg"] = psycopg.__version__
        info["postgresql"] = run_pg("SELECT version()")[0][0]
        info["postgresql_settings"] = dict(run_pg(
            "SELECT name, setting || COALESCE(' ' || unit, '') FROM pg_settings WHERE name = ANY(%(n)s) ORDER BY name",
            {"n": ["shared_buffers", "work_mem", "maintenance_work_mem", "effective_cache_size",
                   "max_parallel_workers_per_gather", "max_connections", "TimeZone", "max_wal_size"]}))
        info["postgresql_current_database"] = run_pg("SELECT current_database(), current_setting('TimeZone')")[0]
    if "neo" in a.engines:
        import neo4j
        info["neo4j_python_driver"] = neo4j.__version__
        info["neo4j"] = [list(r) for r in run_neo("CALL dbms.components() YIELD name, versions, edition RETURN name, versions, edition")]
        info["neo4j_settings"] = dict(run_neo(
            "SHOW SETTINGS YIELD name, value WHERE name IN ['server.memory.heap.initial_size', "
            "'server.memory.heap.max_size', 'server.memory.pagecache.size', 'dbms.memory.transaction.total.max', "
            "'db.transaction.timeout'] RETURN name, value"))
        info["neo4j_database"] = run_neo("CALL db.info() YIELD name RETURN name")[0][0]
    print(json.dumps(info, indent=2, default=str))
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "workspace_info.json").write_text(json.dumps(info, indent=2, default=str))


if __name__ == "__main__":
    main()
