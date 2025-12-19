from langgraph_runtime_inmem.queue import get_num_workers


def get_metrics() -> dict[str, dict[str, int]]:
    from langgraph_api import config

    workers_max = config.N_JOBS_PER_WORKER
    workers_active = get_num_workers()
    return {
        "workers": {
            "max": workers_max,
            "active": workers_active,
            "available": workers_max - workers_active,
        }
    }
