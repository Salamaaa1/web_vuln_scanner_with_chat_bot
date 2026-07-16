import pytest
from app.executors.factory import ExecutorFactory
from app.executors.httpx import HttpxExecutor
from app.executors.nmap import NmapExecutor


@pytest.mark.unit
def test_executor_factory():
    executor = ExecutorFactory.create_executor("httpx")
    assert isinstance(executor, HttpxExecutor)

    executor_nmap = ExecutorFactory.create_executor("nmap")
    assert isinstance(executor_nmap, NmapExecutor)

    with pytest.raises(ValueError):
        ExecutorFactory.create_executor("invalid_tool")


@pytest.mark.excutor
@pytest.mark.asyncio
async def test_httpx_executor():
    executor = HttpxExecutor()
    data = {"url": "https://wikipedia.org"}
    result = await executor.excutor(data)
    assert isinstance(result["httpx_result"], list)
    assert len(result["httpx_result"]) > 0


@pytest.mark.excutor
@pytest.mark.asyncio
async def test_katana_executor():
    from app.executors.katana import KatanaExecutor

    executor = KatanaExecutor()
    result = await executor.excutor({"url": "https://wikipedia.org"})
    assert result["katana_result"]["katana_status"] == "completed"
    assert len(result["katana_result"]["katana_endpoints"]) > 0


@pytest.mark.excutor
@pytest.mark.asyncio
async def test_feroxbuster_executor():
    from app.executors.feroxbuster import FeroxbusterExecutor

    executor = FeroxbusterExecutor()
    data = {"url": "https://wikipedia.org"}
    result = await executor.excutor(data)
    assert result["feroxbuster_result"]["feroxbuster_status"] in ("completed", "failed_or_empty")
    assert isinstance(result["feroxbuster_result"]["feroxbuster_resources"], list)


@pytest.mark.excutor
@pytest.mark.asyncio
async def test_nmap_executor():
    # Scan localhost so the test is fast and does not require external authorization
    executor = NmapExecutor()
    data = {"ip": "127.0.0.1"}
    result = await executor.excutor(data)

    assert result["nmap_result"]["status"] == "completed"
    assert "open_ports" in result["nmap_result"]
    assert "has_web_ports" in result["nmap_result"]


@pytest.mark.excutor
@pytest.mark.asyncio
async def test_nuclei_executor():
    from app.executors.nuclei import NucleiExecutor

    data = {
        "url": "http://example.com",
        "katana_result": {"katana_endpoints": [{"url": "http://example.com/about"}]},
        "feroxbuster_result": {"feroxbuster_resources": [{"url": "http://example.com/.env"}]},
        "httpx_result": [],
    }

    executor = NucleiExecutor()
    result = await executor.excutor(data)
    assert result["nuclei_result"]["nuclei_status"] == "completed"


@pytest.mark.excutor
@pytest.mark.asyncio
async def test_subfinder_executor():
    from app.executors.subfinder import SubfinderExecutor

    executor = SubfinderExecutor()
    data = {"domain": "wikipedia.org"}
    result = await executor.excutor(data)
    assert result["subfinder_result"]["subfinder_status"] == "completed"
    assert len(result["subfinder_result"]["subfinder_subdomains"]) > 0
