"""Create, migrate, and seed an API-only MuckScraper database.

The legacy bootstrap script also created a browser-admin account. The API-only
deployment still needs its safe schema-state handling and default pipeline
configuration, but no account provisioning.
"""

import sys
import time

from sqlalchemy.exc import OperationalError

from aggregator.app import app
from aggregator.seed_defaults import seed_defaults
from bootstrap_admin import prepare_schema, schema_state


def bootstrap_database():
    last_error = None
    for attempt in range(1, 31):
        try:
            state = schema_state()
            break
        except OperationalError as error:
            last_error = error
            print(f"Database not ready yet, retrying ({attempt}/30)...")
            time.sleep(2)
    else:
        raise RuntimeError(f"Database did not become ready: {last_error}")

    print(f"Database state: {state}.")
    prepare_schema(state)
    with app.app_context():
        counts = seed_defaults()
    inserted = sum(value for key, value in counts.items() if key != "topics_backfilled")
    print(
        f"Default config seeded: {inserted} row(s) inserted."
        if inserted
        else "Default config already present."
    )


if __name__ == "__main__":
    try:
        bootstrap_database()
    except Exception as error:
        print(f"Database bootstrap failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
