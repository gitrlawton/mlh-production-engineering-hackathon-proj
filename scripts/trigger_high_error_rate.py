"""
Triggers the High Error Rate alert by sending 20 requests to /debug/error.

Usage:
    uv run python scripts/trigger_high_error_rate.py

Requires FLASK_DEBUG=true in .env and the app to be running on localhost:5000.
"""

import sys
import urllib.request
import urllib.error

BASE_URL = "http://localhost:5000"
ERROR_ENDPOINT = f"{BASE_URL}/debug/error"
NUM_REQUESTS = 20


def main():
    print(f"Sending {NUM_REQUESTS} error requests to {ERROR_ENDPOINT}...")

    for i in range(1, NUM_REQUESTS + 1):
        try:
            urllib.request.urlopen(ERROR_ENDPOINT, timeout=5)
        except urllib.error.HTTPError as e:
            if e.code == 500:
                print(f"  [{i}/{NUM_REQUESTS}] 500 recorded")
            else:
                print(f"  [{i}/{NUM_REQUESTS}] Unexpected status: {e.code}")
                sys.exit(1)
        except Exception as e:
            print(f"\nError: could not reach {ERROR_ENDPOINT} — is the app running?")
            print(f"Details: {e}")
            sys.exit(1)

    print(f"\nDone. Error rate is now above the 10% threshold.")
    print("Check http://localhost:5000/alerts — the alert should fire within 30 seconds.")


if __name__ == "__main__":
    main()
