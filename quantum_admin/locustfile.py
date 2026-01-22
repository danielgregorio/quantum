"""
Performance Benchmarking with Locust
Load testing for Quantum Admin API endpoints

Usage:
    # Run with UI
    locust -f locustfile.py --host=http://localhost:8000

    # Run headless
    locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 1m --headless

    # Run specific test class
    locust -f locustfile.py HealthCheckUser --host=http://localhost:8000
"""

from locust import HttpUser, task, between, events
import random
import json


class HealthCheckUser(HttpUser):
    """
    User that only checks health endpoint
    Simulates monitoring/health check traffic
    """
    wait_time = between(1, 3)

    @task
    def health_check(self):
        """GET /health"""
        self.client.get("/health")


class AuthenticationUser(HttpUser):
    """
    User performing authentication operations
    Tests login, token refresh, user info retrieval
    """
    wait_time = between(2, 5)

    def on_start(self):
        """Setup - register user before tests"""
        self.username = f"loadtest_user_{random.randint(1000, 9999)}"
        self.password = "LoadTest123!"

        # Register user
        self.client.post("/auth/register", json={
            "username": self.username,
            "email": f"{self.username}@example.com",
            "password": self.password,
            "full_name": "Load Test User"
        })

    @task(3)
    def login(self):
        """POST /auth/login - Most common operation"""
        response = self.client.post("/auth/login", json={
            "username": self.username,
            "password": self.password
        })

        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(1)
    def get_current_user(self):
        """GET /auth/me - Requires authentication"""
        if hasattr(self, 'token'):
            self.client.get("/auth/me", headers={
                "Authorization": f"Bearer {self.token}"
            })


class ContainerManagementUser(HttpUser):
    """
    User managing Docker containers
    Tests container listing and operations
    """
    wait_time = between(3, 7)

    @task(5)
    def list_containers(self):
        """GET /containers - Most frequent operation"""
        self.client.get("/containers")

    @task(2)
    def list_images(self):
        """GET /images"""
        self.client.get("/images")

    @task(1)
    def get_container_stats(self):
        """GET /containers/{id}/stats"""
        # Using a likely non-existent ID to test 404 handling
        self.client.get("/containers/test123/stats")


class SchemaInspectionUser(HttpUser):
    """
    User inspecting database schema
    Tests schema-related endpoints
    """
    wait_time = between(5, 10)

    @task(3)
    def inspect_schema(self):
        """GET /schema/inspect"""
        self.client.get("/schema/inspect")

    @task(2)
    def generate_models(self):
        """GET /schema/models"""
        self.client.get("/schema/models")

    @task(2)
    def export_mermaid(self):
        """GET /schema/export?format=mermaid"""
        self.client.get("/schema/export", params={"format": "mermaid"})

    @task(1)
    def export_dbml(self):
        """GET /schema/export?format=dbml"""
        self.client.get("/schema/export", params={"format": "dbml"})


class AIAssistantUser(HttpUser):
    """
    User interacting with AI assistant
    Tests AI chat and function calling
    """
    wait_time = between(2, 5)

    @task(5)
    def chat_with_ai(self):
        """POST /ai/chat"""
        messages = [
            "How do I create a migration?",
            "Generate SQL to get all users",
            "Show me the database schema",
            "Create a Product model",
            "What is SQLAlchemy?"
        ]

        self.client.post("/ai/chat", json={
            "message": random.choice(messages),
            "use_slm": False  # Use rule-based for performance
        })

    @task(1)
    def list_ai_functions(self):
        """GET /ai/functions"""
        self.client.get("/ai/functions")


class PipelineEditorUser(HttpUser):
    """
    User working with CI/CD pipelines
    Tests pipeline parsing and generation
    """
    wait_time = between(4, 8)

    @task(3)
    def get_templates(self):
        """GET /pipelines/templates"""
        self.client.get("/pipelines/templates")

    @task(2)
    def parse_pipeline(self):
        """POST /pipelines/parse"""
        qpipeline = """<?xml version="1.0"?>
<q:pipeline name="Build and Test">
    <q:stage name="Build">
        <q:step>npm install</q:step>
        <q:step>npm run build</q:step>
    </q:stage>
    <q:stage name="Test">
        <q:step>npm test</q:step>
    </q:stage>
</q:pipeline>"""

        self.client.post("/pipelines/parse", json={
            "qpipeline": qpipeline
        })

    @task(1)
    def generate_jenkinsfile(self):
        """POST /pipelines/generate"""
        self.client.post("/pipelines/generate", json={
            "name": "Test Pipeline",
            "stages": [
                {
                    "name": "Build",
                    "steps": ["npm install", "npm run build"]
                }
            ]
        })


class MixedWorkloadUser(HttpUser):
    """
    User performing mixed operations
    Realistic workload simulation
    """
    wait_time = between(2, 6)

    def on_start(self):
        """Setup - login once"""
        self.username = f"mixed_user_{random.randint(1000, 9999)}"
        self.password = "Test123!"

        self.client.post("/auth/register", json={
            "username": self.username,
            "email": f"{self.username}@example.com",
            "password": self.password,
            "full_name": "Mixed User"
        })

        response = self.client.post("/auth/login", json={
            "username": self.username,
            "password": self.password
        })

        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(10)
    def check_health(self):
        """Health checks - most frequent"""
        self.client.get("/health")

    @task(5)
    def list_containers(self):
        """Container operations"""
        self.client.get("/containers")

    @task(3)
    def ai_chat(self):
        """AI assistant"""
        self.client.post("/ai/chat", json={
            "message": "Help me with database",
            "use_slm": False
        })

    @task(2)
    def inspect_schema(self):
        """Schema inspection"""
        self.client.get("/schema/inspect")

    @task(1)
    def get_user_info(self):
        """Get current user"""
        if hasattr(self, 'token'):
            self.client.get("/auth/me", headers={
                "Authorization": f"Bearer {self.token}"
            })


# ============================================================================
# Custom Events and Reporting
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts"""
    print("🚀 Performance test starting...")
    print(f"   Target: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops - print summary"""
    print("\n" + "="*80)
    print("📊 PERFORMANCE TEST SUMMARY")
    print("="*80)

    stats = environment.stats

    print(f"\nTotal requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Failure rate: {stats.total.fail_ratio * 100:.2f}%")

    print(f"\nResponse times:")
    print(f"  Average: {stats.total.avg_response_time:.2f}ms")
    print(f"  Median: {stats.total.median_response_time:.2f}ms")
    print(f"  Min: {stats.total.min_response_time:.2f}ms")
    print(f"  Max: {stats.total.max_response_time:.2f}ms")

    print(f"\nPercentiles:")
    for percentile, value in stats.total.get_response_time_percentile([50, 75, 90, 95, 99]).items():
        print(f"  p{percentile}: {value:.2f}ms")

    print(f"\nRequests/second: {stats.total.total_rps:.2f}")

    # Print endpoint statistics
    print("\n" + "-"*80)
    print("ENDPOINT STATISTICS")
    print("-"*80)

    for entry in stats.entries.values():
        if entry.num_requests > 0:
            print(f"\n{entry.method} {entry.name}")
            print(f"  Requests: {entry.num_requests}")
            print(f"  Failures: {entry.num_failures} ({entry.fail_ratio * 100:.1f}%)")
            print(f"  Avg: {entry.avg_response_time:.2f}ms")
            print(f"  p95: {entry.get_response_time_percentile(0.95):.2f}ms")
            print(f"  RPS: {entry.total_rps:.2f}")

    print("\n" + "="*80)

    # Performance goals check
    print("\n🎯 PERFORMANCE GOALS CHECK")
    print("-"*80)

    goals_met = True

    # Goal 1: p95 < 200ms
    p95 = stats.total.get_response_time_percentile(0.95)
    p95_goal = p95 < 200

    print(f"✅ p95 < 200ms: {p95:.2f}ms" if p95_goal else f"❌ p95 < 200ms: {p95:.2f}ms")
    goals_met = goals_met and p95_goal

    # Goal 2: Failure rate < 1%
    failure_rate = stats.total.fail_ratio * 100
    failure_goal = failure_rate < 1

    print(f"✅ Failure rate < 1%: {failure_rate:.2f}%" if failure_goal else f"❌ Failure rate < 1%: {failure_rate:.2f}%")
    goals_met = goals_met and failure_goal

    # Goal 3: Average < 100ms
    avg_goal = stats.total.avg_response_time < 100

    print(f"✅ Average < 100ms: {stats.total.avg_response_time:.2f}ms" if avg_goal else f"❌ Average < 100ms: {stats.total.avg_response_time:.2f}ms")
    goals_met = goals_met and avg_goal

    print("\n" + "="*80)

    if goals_met:
        print("🎉 ALL PERFORMANCE GOALS MET!")
    else:
        print("⚠️  Some performance goals not met - optimization needed")

    print("="*80 + "\n")


# ============================================================================
# Usage Examples
# ============================================================================

"""
USAGE EXAMPLES:

1. Quick test (10 users, 1 minute):
   locust -f locustfile.py --host=http://localhost:8000 \\
          --users 10 --spawn-rate 2 --run-time 1m --headless

2. Moderate load (100 users, 5 minutes):
   locust -f locustfile.py --host=http://localhost:8000 \\
          --users 100 --spawn-rate 10 --run-time 5m --headless

3. Heavy load (500 users):
   locust -f locustfile.py --host=http://localhost:8000 \\
          --users 500 --spawn-rate 50 --run-time 10m --headless

4. Spike test (0 → 1000 users quickly):
   locust -f locustfile.py --host=http://localhost:8000 \\
          --users 1000 --spawn-rate 100 --run-time 2m --headless

5. With web UI (for real-time monitoring):
   locust -f locustfile.py --host=http://localhost:8000
   # Then open http://localhost:8089

6. Test specific user type:
   locust -f locustfile.py MixedWorkloadUser --host=http://localhost:8000

7. Export results to CSV:
   locust -f locustfile.py --host=http://localhost:8000 \\
          --users 100 --spawn-rate 10 --run-time 5m --headless \\
          --csv=results/loadtest
"""
