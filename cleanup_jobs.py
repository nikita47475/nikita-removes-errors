from pathlib import Path
import shutil
from app.config import JOBS_DIR

# Optional scheduled cleanup. Run periodically (for example, via cron/Task Scheduler)
# to remove job directories older than a chosen retention window.
for p in JOBS_DIR.iterdir():
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
print('Temporary jobs cleaned.')
