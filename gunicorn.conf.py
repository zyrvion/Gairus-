def post_worker_init(worker):
    # Socket Mode est démarré exclusivement par slack_worker.py.
    # Ne pas le démarrer dans Gunicorn afin d'éviter deux connexions
    # Slack concurrentes dans deux processus différents.
    print(
        "[GAIRUS][SLACK] Socket Mode géré par slack_worker.py",
        flush=True,
    )
