import redis


# Check arguments.
if len(sys.argv) < 3:
    print("Error: missing arguments.")
    print("Usage: graph2redis.py <input-edgelist> <redis-port>")
    sys.exit(1)

with open(sys.argv[1], 'rb') as f:
    edges = pickle.load(f)

r = redis.StrictRedis(host='localhost', port=int(sys.argv[2]), db=0)

for edge in edges:
    uid, rid = edge
    r.sadd('users', uid)
    r.sadd('repos', rid)
    r.sadd(f'user:{uid}', rid)
    r.sadd(f'repo:{rid}', uid)
