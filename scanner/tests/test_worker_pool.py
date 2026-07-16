import pytest
from app.core.worker_pool import WorkerPool
from app.executors.base import Executor, Worker

class MockExecutor(Executor):
    async def excutor(self, data: dict) -> dict:
        data["mock_status"] = "completed"
        return data

@pytest.mark.unit
@pytest.mark.asyncio
async def test_worker_pool_with_mocked_executor():
    # WorkerPool no longer reads fields off `target` (it sizes the pool from
    # the workers list), so a real Beanie Document with a DB connection isn't needed here.
    target = None
    executor = MockExecutor()

    pool = WorkerPool()
    workers = [
        Worker(executor, {"ip": "1.1.1.1"}, "mock"),
        Worker(executor, {"ip": "2.2.2.2"}, "mock"),
        Worker(executor, {"ip": "3.3.3.3"}, "mock"),
    ]

    results = await pool.execute_target(target, workers)

    assert len(results) == 3
    assert all(res["mock_status"] == "completed" for res in results)
    assert pool.pollSize == 3
