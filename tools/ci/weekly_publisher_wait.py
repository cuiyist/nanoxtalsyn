"""Wait for the latest main publisher, without changing scan or receipt validation."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import time


INTERVAL = 30 * 60
FIRST_WINDOW = range(11)  # immediately, then every 30 minutes to hour five
LAST_WINDOW = range(11, 13)
PUBLISH_EVENTS = {"workflow_run", "workflow_dispatch"}
ACTIVE = {"queued", "in_progress", "requested", "waiting", "pending"}


def newest_main_run(runs):
    return max(
        (r for r in runs if r["head_branch"] == "main" and r["event"] in PUBLISH_EVENTS),
        key=lambda r: (r["created_at"], r["id"]), default=None,
    )


def publisher_run(repo):
    endpoint = f"repos/{repo}/actions/workflows/site-publish.yml/runs?branch=main&per_page=30"
    body = subprocess.check_output(["gh", "api", endpoint], timeout=60)
    return newest_main_run(json.loads(body)["workflow_runs"])


def wait_for_publisher(started, slots, latest, *, clock=time.time, sleep=time.sleep, log=print):
    for slot in slots:
        target = started + slot * INTERVAL
        remaining = target - clock()
        if remaining > 0:
            sleep(remaining)
        run = latest()
        if run is None:
            return True  # The scan will still require its normal receipts.
        status = run["status"]
        log(f"Publisher {run['id']} is {status} at poll {slot + 1}.")
        if status == "completed":
            return True  # No substitution: success/receipt checks are in the scan.
        if status not in ACTIVE:
            raise RuntimeError(f"Unrecognized publisher status: {status}")
        if clock() >= started + 12 * INTERVAL:
            break
    return False


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--finish", type=int, metavar="STARTED_AT")
    args = ap.parse_args()
    started = int(time.time()) if args.finish is None else args.finish
    window = FIRST_WINDOW if args.finish is None else LAST_WINDOW
    ready = wait_for_publisher(started, window, lambda: publisher_run(os.environ["GITHUB_REPOSITORY"]))
    if args.finish is not None and not ready:
        raise SystemExit("No publisher completed within the six-hour binding wait; scan not run.")
    with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
        print(f"started_at={started}", file=output)
        print(f"ready={str(ready).lower()}", file=output)


if __name__ == "__main__":
    main()
