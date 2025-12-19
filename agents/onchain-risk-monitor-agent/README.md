# onchain risk & anomaly monitor agent (warden community agent)

this is a langgraph-based agent that monitors onchain activity and produces a risk report when it detects abnormal behavior.

## what this agent does
given a chain + a list of target addresses (contracts or wallets), the agent:
- pulls recent transactions/events (read-only)
- runs anomaly checks (tx spikes, big outflows, pause/admin signals, tvl drops when available)
- returns a structured risk report as json
- (optional) can generate a webhook payload you can forward to discord/slack/etc

## security / limitations (phase 1)
- read-only: this agent does **not** access user wallets
- no signing: it does **not** send transactions
- it does **not** store anything on warden infrastructure

## api endpoints
base url: http://localhost:8000

- GET /health
  - returns: { "status": "ok" }

- POST /analyze
  - request json:
    {
      "chain": "ethereum",
      "targets": ["0x...","0x..."],
      "window_minutes": 60,
      "risk_profile": "balanced"
    }

  - response json (example shape):
    {
      "chain": "ethereum",
      "window_minutes": 60,
      "targets": ["0x..."],
      "risk_score": 42,
      "signals_triggered": [
        {"name":"tx_spike","severity":"medium","details":"..."}
      ],
      "recommended_actions": [
        "monitor closely for 1-2 hours",
        "verify admin actions if any",
        "pause integrations if risk increases"
      ]
    }

## required environment variables
create a file named .env in this folder (same level as this readme).
you can copy .env.example to .env.

- RPC_URL_ETH (required)
  - an ethereum rpc url from alchemy/infura/ankr/quicknode/etc
- ETHERSCAN_API_KEY (optional)
- ALERT_WEBHOOK_URL (optional)
- DEFILLAMA_BASE_URL (optional; default is set in .env.example)

## how to run locally (windows powershell)
from this folder:

1) create venv
   python -m venv .venv

2) activate venv
   .\.venv\Scripts\Activate.ps1

3) install deps
   pip install -r requirements.txt

4) run api
   uvicorn src.server:app --host 0.0.0.0 --port 8000 --reload

5) test health
   curl http://127.0.0.1:8000/health

6) test analyze
   curl -X POST http://127.0.0.1:8000/analyze 
     -H "Content-Type: application/json" 
     -d "{\"chain\":\"ethereum\",\"targets\":[\"0x0000000000000000000000000000000000000000\"],\"window_minutes\":60,\"risk_profile\":\"balanced\"}"

## how to deploy
option a: langgraph cloud
- deploy one agent per langgraph instance
- set the same env vars in your cloud deployment
- expose the public url and use that for warden agent hub integration later

option b: self-host
- deploy this fastapi server on a vps or platform (render/fly/railway)
- set env vars securely
- make sure /health and /analyze are reachable publicly

## project structure
- src/sources.py  -> fetches data (rpc, defillama)
- src/rules.py    -> anomaly rules + scoring
- src/graph.py    -> langgraph workflow wiring
- src/server.py   -> fastapi server exposing /health and /analyze
- tests/          -> basic tests (optional but recommended)
