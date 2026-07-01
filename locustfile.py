import random
from locust import HttpUser, between, events, task
from locust.runners import MasterRunner, LocalRunner


SAMPLE_URLS = [
    "https://github.com",
    "https://example.com",
    "https://python.org",
    "https://flask.palletsprojects.com",
    "https://docs.locust.io",
]


class UrlShortenerUser(HttpUser):
    wait_time = between(1, 3)
    short_codes = []

    @task(3)
    def visit_homepage(self):
        self.client.get("/")

    @task(2)
    def shorten_url(self):
        url = random.choice(SAMPLE_URLS)
        response = self.client.post(
            "/shorten",
            json={"url": url},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code == 201:
            short_code = response.json().get("short_code")
            if short_code:
                UrlShortenerUser.short_codes.append(short_code)

    @task(2)
    def follow_redirect(self):
        if not UrlShortenerUser.short_codes:
            self.visit_homepage()
            return
        short_code = random.choice(UrlShortenerUser.short_codes)
        self.client.get(f"/{short_code}", allow_redirects=False, name="/<short_code>")

    @task(1)
    def check_metrics(self):
        self.client.get("/metrics")


@events.quitting.add_listener
def print_summary(environment, **kwargs):
    if not isinstance(environment.runner, (LocalRunner, MasterRunner)):
        return

    stats = environment.runner.stats
    print("\n" + "=" * 70)
    print(f"  LOAD TEST SUMMARY — {environment.host}")
    print("=" * 70)
    print(f"  {'Endpoint':<30} {'Reqs':>6} {'Fails':>6} {'Avg':>6} {'p95':>6} {'RPS':>7}")
    print("  " + "-" * 68)

    for entry in sorted(stats.entries.values(), key=lambda e: e.name):
        print(
            f"  {entry.method + ' ' + entry.name:<30}"
            f" {entry.num_requests:>6}"
            f" {entry.num_failures:>6}"
            f" {int(entry.avg_response_time):>5}ms"
            f" {int(entry.get_response_time_percentile(0.95)):>5}ms"
            f" {entry.current_rps:>7.1f}"
        )

    total = stats.total
    print("  " + "-" * 68)
    print(
        f"  {'TOTAL':<30}"
        f" {total.num_requests:>6}"
        f" {total.num_failures:>6}"
        f" {int(total.avg_response_time):>5}ms"
        f" {int(total.get_response_time_percentile(0.95)):>5}ms"
        f" {total.current_rps:>7.1f}"
    )
    print("=" * 70)
    failure_rate = (total.num_failures / total.num_requests * 100) if total.num_requests else 0
    print(f"  Users: {environment.runner.target_user_count} concurrent   Failure rate: {failure_rate:.1f}%")
    print("=" * 70 + "\n")
