# W23 CI, Security and Supply-Chain Contract

W23 expands the W02 scaffold without changing forecast science. Core CI runs on Windows and Linux with Python 3.12 using the same unit/integrity commands as local validation. The base package remains dependency-free. The optional W22 FastAPI adapter is isolated behind `requirements/product.lock` and is tested separately.

Security controls include repository secret/forbidden-artifact scanning, exact direct product pins, a reviewed lock file for the tested product environment, `pip check`, GitHub CodeQL, and pull-request dependency review. Runtime environment manifests record package/runtime versions without dumping arbitrary environment variables or credentials.

The lock records the versions exercised during W23 (`fastapi 0.128.2`, `uvicorn 0.48.0` plus transitive runtime packages). It is a tested reproducibility surface, not a claim those versions are universally optimal or permanently current.
