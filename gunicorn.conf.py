def post_worker_init(worker):
    from slack_gateway import start_slack_socket_mode
    start_slack_socket_mode()
