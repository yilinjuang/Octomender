import multiprocessing

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
timeout = 300  # Large enough to avoid worker timeout caused by time-consuming suggesting

# HTTPS and forwarding proxies
forwarded_allow_ips = '*'
secure_scheme_headers = {'X-FORWARDED-PROTO': 'https'}

# Logging
log_level = 'DEBUG'
