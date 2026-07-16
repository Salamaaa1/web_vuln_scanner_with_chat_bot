# Test Output - Prompt 1

Toutes les étapes de test pour les exécuteurs du pipeline URL ont été exécutées avec succès sous pytest (avec mocks actifs).

## Résultat de la suite de tests (pytest) :

```text
============================= test session starts ==============================
platform linux -- Python 3.14.5, pytest-8.4.2, pluggy-1.6.0 -- /home/oss/Projects/Presistent/auto_pentest/scanner/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/oss/Projects/Presistent/auto_pentest/scanner
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.14.0, asyncio-1.4.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 7 items                                                              

tests/test_executors.py::test_executor_factory PASSED                    [ 14%]
tests/test_executors.py::test_httpx_executor PASSED                      [ 28%]
tests/test_executors.py::test_katana_executor PASSED                     [ 42%]
tests/test_executors.py::test_feroxbuster_executor PASSED                [ 57%]
tests/test_executors.py::test_nuclei_executor PASSED                     [ 71%]
tests/test_pipelines.py::test_url_pipeline_build PASSED                  [ 85%]
tests/test_worker_pool.py::test_worker_pool_with_mocked_executor PASSED  [100%]

============================== 7 passed in 0.56s ===============================
```
