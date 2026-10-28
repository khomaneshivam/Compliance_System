"""
PlantProof Locust Load Testing Suite
Simulates realistic concurrent user workloads across Plant Managers, EHS Directors,
Auditors, and Background Ingestion pipelines.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import time
from locust import HttpUser, task, between, events
from tests.load.safety_guard import validate_load_test_target, LoadTestSafetyViolation


@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    """
    CRITICAL SAFETY CHECK:
    Validates that the host target is strictly local before starting load testing.
    """
    target = environment.host or "http://localhost:8000"
    try:
        validate_load_test_target(target)
        print(f"\n[LOCUST SAFETY GUARD] Target validated: '{target}' (Local test stack confirmed)")
    except LoadTestSafetyViolation as exc:
        print(f"\n[LOCUST SAFETY GUARD CRITICAL ERROR] {exc}")
        environment.runner.quit()
        raise SystemExit(1)


class PlantManagerUser(HttpUser):
    """Simulates facility leadership inspecting compliance health and registers."""
    weight = 3
    wait_time = between(1.0, 3.0)
    token = None
    plant_id = None
    _cached_token = None
    _cached_plant_id = None

    def on_start(self):
        """Authenticates as demo Plant Manager (cached per session pool)."""
        if not PlantManagerUser._cached_token:
            login_resp = self.client.post(
                "/api/v1/auth/login",
                json={"email": "rohit.sharma@acme-mfg.in", "password": "DemoPass123!"},
                name="Auth: Login (Plant Manager)"
            )
            if login_resp.status_code == 200:
                PlantManagerUser._cached_token = login_resp.json().get("access_token")
                plants_resp = self.client.get(
                    "/api/v1/plants",
                    headers={"Authorization": f"Bearer {PlantManagerUser._cached_token}"},
                    name="Facilities: List Plants"
                )
                if plants_resp.status_code == 200 and len(plants_resp.json()) > 0:
                    PlantManagerUser._cached_plant_id = plants_resp.json()[0]["id"]
        self.token = PlantManagerUser._cached_token
        self.plant_id = PlantManagerUser._cached_plant_id

    @task(4)
    def view_facility_requirements(self):
        """Reads facility requirements register."""
        if not self.token or not self.plant_id:
            return
        self.client.get(
            f"/api/v1/companies/{self.plant_id}/requirements",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Requirements: Get Plant Obligations"
        )

    @task(3)
    def browse_master_requirements_paginated(self):
        """Faceted pagination query on statutory master catalog."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/master-data/requirements?page=1&page_size=20",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Master Data: Paginated Requirements"
        )

    @task(2)
    def view_facility_profile(self):
        """Reads operational facts snapshot."""
        if not self.token or not self.plant_id:
            return
        self.client.get(
            f"/api/v1/plants/{self.plant_id}/profile",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Facilities: Get Plant Profile"
        )


class EHSManagerUser(HttpUser):
    """Simulates EHS Compliance Director managing tasks, evidence, and circulars."""
    weight = 2
    wait_time = between(1.5, 4.0)
    token = None
    _cached_token = None

    def on_start(self):
        """Authenticates as demo EHS Manager (cached per session pool)."""
        if not EHSManagerUser._cached_token:
            login_resp = self.client.post(
                "/api/v1/auth/login",
                json={"email": "priya.deshmukh@acme-mfg.in", "password": "DemoPass123!"},
                name="Auth: Login (EHS Manager)"
            )
            if login_resp.status_code == 200:
                EHSManagerUser._cached_token = login_resp.json().get("access_token")
        self.token = EHSManagerUser._cached_token

    @task(3)
    def list_documents(self):
        """Browses compliance evidence vault metadata."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Documents: List Evidence Vault"
        )

    @task(3)
    def list_tasks(self):
        """Reads open remediation tasks."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/tasks",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Tasks: List Remediation Items"
        )

    @task(2)
    def view_regulatory_changes(self):
        """Inspects gazette changes and candidate impacts."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/regulatory/changes",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Regulatory: List Changes Inbox"
        )


class AuditorUser(HttpUser):
    """Simulates read-only auditor inspecting readiness reports and authorities."""
    weight = 1
    wait_time = between(2.0, 5.0)
    token = None
    _cached_token = None

    def on_start(self):
        """Authenticates as demo Auditor (cached per session pool)."""
        if not AuditorUser._cached_token:
            login_resp = self.client.post(
                "/api/v1/auth/login",
                json={"email": "sneha.patil@acme-mfg.in", "password": "DemoPass123!"},
                name="Auth: Login (Auditor)"
            )
            if login_resp.status_code == 200:
                AuditorUser._cached_token = login_resp.json().get("access_token")
        self.token = AuditorUser._cached_token

    @task(2)
    def list_authorities_and_acts(self):
        """Reads regulatory authorities and statutes."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/master-data/authorities",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Master Data: List Authorities"
        )
        self.client.get(
            "/api/v1/master-data/acts",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Master Data: List Acts"
        )

    @task(1)
    def list_reports(self):
        """Inspects generated audit reports."""
        if not self.token:
            return
        self.client.get(
            "/api/v1/reports",
            headers={"Authorization": f"Bearer {self.token}"},
            name="Reports: List Readiness Reports"
        )
