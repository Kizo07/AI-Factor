# AI Exposure Dashboard — FastAPI backend

Loopback-only JSON API serving the same offline data files and analysis
functions as the legacy Streamlit app (`dashboard/app.py`), for the new
Mantine frontend (`dashboard/frontend/`).

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | liveness |
| GET | `/api/meta` | as-of dates, window, coverage metadata |
| GET | `/api/exposure?model=ff\|market` | precomputed cross-section (default 252d window) |
| POST | `/api/exposure/recompute` | recompute cross-section for a custom `[start_date, end_date]` period (`{"start_date","end_date","model"}`) |
| GET | `/api/factors` | AI factor daily series (theme/infra excess, rf) |
| GET | `/api/ff` | daily Fama-French 5 factors + momentum |
| GET | `/api/returns?ticker=X` | daily returns for one ticker |
| GET | `/api/constituents` | S&P 500 constituents (ticker, name, sector) |
| GET | `/api/trading-days` | sorted unique trading days |
| GET | `/api/rolling-betas?ticker=X&window=252&model=ff` | rolling beta series for one stock |

All data is read from `data/` under the project root; nothing is fetched from
the network. NaN values are serialized as `null`.

## Run

```bash
# from the project root (AI-Factor/)
.venv/bin/uvicorn dashboard.backend.app:app --host 127.0.0.1 --port 8000
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8000`, so in normal
development you only need to start this backend and `npm run dev` in
`dashboard/frontend/`.