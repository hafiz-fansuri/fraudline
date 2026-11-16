import logging
import time

from fraudline.monitor import monitor_once

while True:
    try:
        monitor_once(retrain=True)
    except Exception:
        logging.exception("Monitoring failed; previous report is preserved")
    time.sleep(300)
