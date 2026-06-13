"""Phase 13.7d: Deployment smoke tests.

Validates docker-compose.prod.yaml structure, health endpoint,
coordinator accessibility, and hermes-bridge connectivity.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
import yaml


PROD_COMPOSE = Path(__file__).resolve().parent.parent / "docker-compose.prod.yaml"


class TestComposeProdStructure:
    """Validate docker-compose.prod.yaml has required services."""

    @pytest.fixture()
    def compose_data(self):
        return yaml.safe_load(PROD_COMPOSE.read_text())

    def test_file_exists(self):
        assert PROD_COMPOSE.exists(), "docker-compose.prod.yaml missing"

    def test_coordinator_service_defined(self, compose_data):
        svc = compose_data["services"].get("coordinator")
        assert svc is not None, "coordinator service missing"

    def test_coordinator_has_healthcheck(self, compose_data):
        hc = compose_data["services"]["coordinator"].get("healthcheck")
        assert hc is not None, "coordinator healthcheck missing"
        assert "test" in hc
        assert "/api/v1/health" in str(hc["test"])

    def test_coordinator_has_resource_limits(self, compose_data):
        deploy = compose_data["services"]["coordinator"].get("deploy", {})
        limits = deploy.get("resources", {}).get("limits", {})
        assert "memory" in limits, "memory limit missing"
        assert "cpus" in limits, "cpu limit missing"

    def test_coordinator_exposes_port(self, compose_data):
        ports = compose_data["services"]["coordinator"].get("ports", [])
        assert len(ports) > 0, "no port mapping"
        assert "8000" in str(ports[0])

    def test_hermes_bridge_service_defined(self, compose_data):
        svc = compose_data["services"].get("hermes-bridge")
        assert svc is not None, "hermes-bridge service missing"

    def test_bridge_depends_on_coordinator_healthy(self, compose_data):
        deps = compose_data["services"]["hermes-bridge"].get("depends_on", {})
        coord_dep = deps.get("coordinator", {})
        assert coord_dep.get("condition") == "service_healthy"

    def test_bridge_has_agora_url(self, compose_data):
        env = compose_data["services"]["hermes-bridge"].get("environment", [])
        assert any("AGORA_URL" in str(e) for e in env)

    def test_volumes_defined(self, compose_data):
        vols = compose_data.get("volumes", {})
        assert "agora_data" in vols
        assert "hermes_data" in vols
