import pytest
from app.pipelines.url_pipeline import UrlPipeline
from app.pipelines.dns_pipeline import DnsPipeline
from app.pipelines.machine_pipeline import MachinePipeline
from app.pipelines.base import Step

@pytest.mark.unit
def test_url_pipeline_build():
    pipeline = UrlPipeline()
    pipeline.pipeline_build({"url": "https://example.com"})

    # 2 steps: [httpx, katana, feroxbuster, nmap] then [nuclei]
    assert len(pipeline.steps) == 2
    assert len(pipeline.steps[0].workers) == 4
    assert {w.executor_name for w in pipeline.steps[0].workers} == {"httpx", "katana", "feroxbuster", "nmap"}
    assert len(pipeline.steps[1].workers) == 1
    assert pipeline.steps[1].workers[0].executor_name == "nuclei"


@pytest.mark.unit
def test_dns_pipeline_build():
    pipeline = DnsPipeline()
    pipeline.pipeline_build({"domain": "example.com"})

    # 2 steps: [subfinder, nmap] then [httpx]
    assert len(pipeline.steps) == 2
    assert {w.executor_name for w in pipeline.steps[0].workers} == {"subfinder", "nmap"}
    assert pipeline.steps[1].workers[0].executor_name == "httpx"
    # The domain key must be propagated to every worker's shared data dict
    assert pipeline.steps[0].workers[0].data["domain"] == "example.com"


@pytest.mark.unit
def test_machine_pipeline_build():
    pipeline = MachinePipeline()
    pipeline.pipeline_build({"ip": "192.168.1.1"})

    # 3 sequential steps: [nmap], [httpx], [nuclei]
    assert len(pipeline.steps) == 3
    assert pipeline.steps[0].workers[0].executor_name == "nmap"
    assert pipeline.steps[1].workers[0].executor_name == "httpx"
    assert pipeline.steps[2].workers[0].executor_name == "nuclei"
