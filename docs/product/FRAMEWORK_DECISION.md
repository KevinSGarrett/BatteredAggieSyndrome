# W22 Product Framework Decision

## Decision
Use a framework-neutral, dependency-free Python serving core plus an **optional FastAPI adapter**. Serve the initial dashboard as static HTML/CSS/JavaScript from the same FastAPI process.

Base package dependencies remain empty. Install the product adapter with:

```bash
pip install -e ".[product]"
```

Then run:

```bash
python tools/run_product.py --snapshot-root <published-forecast-root>
```

## Why
- Snapshot serving is read-heavy and does not need a second inference or feature-computation service.
- FastAPI provides an OpenAPI-oriented HTTP surface and can mount static files in the same application.
- A build-free static dashboard avoids a React toolchain before product complexity justifies one.
- Streamlit remains a credible rapid-analysis UI, but using it as the primary W22 product would create a second application/runtime and encourage Python rerun logic in the presentation surface.
- The pure Python `ForecastProductService` remains the canonical boundary, so FastAPI can be replaced later without altering forecast semantics.

## Alternatives retained
- **Streamlit:** deferred for analyst/research views or rapid prototypes.
- **React:** deferred until richer interaction, component reuse or frontend-team needs justify a build pipeline.
- **PostgreSQL:** still conditional; immutable local artifact serving does not demonstrate a transactional/concurrent persistence requirement yet.

## Current official documentation checked (2026-08-08)
- FastAPI: static files, dependency injection and OpenAPI/features documentation.
- Streamlit: current multipage architecture and `st.navigation` guidance.

This is an evidence-backed Level-B implementation choice, not a new invariant.
