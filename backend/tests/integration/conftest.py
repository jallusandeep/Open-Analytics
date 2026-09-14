import uuid
from pathlib import Path

import httpx
import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage
from testcontainers.core.wait_strategies import HttpWaitStrategy


@pytest.fixture(scope="session")
def api_container():
    backend = Path(__file__).resolve().parents[2]
    with DockerImage(path=str(backend), dockerfile_path="tests/Dockerfile", tag=f"open-analytics-test:{uuid.uuid4().hex}", clean_up=True) as image:
        container = DockerContainer(str(image)).with_exposed_ports(8000)
        container.waiting_for(HttpWaitStrategy(8000, path="/health").for_status_code(200).with_startup_timeout(120))
        with container:
            yield container


@pytest.fixture
def api(api_container):
    url = f"http://{api_container.get_container_host_ip()}:{api_container.get_exposed_port(8000)}"
    with httpx.Client(base_url=url, timeout=30) as client:
        yield client


@pytest.fixture
def account(api):
    payload = {"full_name": "Integration User", "email": f"test-{uuid.uuid4().hex}@example.com", "password": "StrongPassword123!"}
    response = api.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 200, response.text
    return {**payload, **response.json()}


@pytest.fixture
def admin_headers(api, api_container, account):
    # Promote a generated test account via the real database, never production credentials.
    code = "from app.database import get_connection; c=get_connection(); c.execute(\"UPDATE users SET role='admin' WHERE user_id=?\", [" + repr(account["user_id"]) + "]); c.close()"
    result = api_container.exec(["python", "-c", code])
    assert result.exit_code == 0, result.output
    response = api.post("/api/v1/auth/login", json={"login_identifier": account["email"], "password": account["password"]})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
