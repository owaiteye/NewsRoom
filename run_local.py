"""Phone/manual backup: same pipeline, reads .env file. Usage: python run_local.py [--dry-run]"""
import os
import sys

def _load_dotenv(path=".env"):
    if not os.path.exists(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

if __name__ == "__main__":
    _load_dotenv()
    if "--dry-run" not in sys.argv:
        sys.argv.append("--dry-run")  # SAFE DEFAULT on phone: preview only unless you pass --live
        if "--live" in sys.argv:
            sys.argv.remove("--dry-run"); sys.argv.remove("--live")
        print("run_local: DRY-RUN preview (pass --live to actually post).")
    import main as m
    # emulate: python main.py --mode digest [--dry-run]
    sys.argv = ["main.py", "--mode", "digest"] + (["--dry-run"] if "--dry-run" in sys.argv else [])
    m.main()
