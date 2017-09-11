import json
import os
import pickle
import sys
from multiprocessing import Pool


# Check arguments.
if len(sys.argv) < 4:
    print("Error: missing arguments.")
    print("Usage: parse.py {-m|--member|-w|--watch} {<input-json-directory>|<input-json-file>} <output-data-basename> [n-process]")
    sys.exit(1)

if sys.argv[1] in ["-m", "--member"]:
    EVENT_TYPE = "MemberEvent"
elif sys.argv[1] in ["-w", "--watch"]:
    EVENT_TYPE = "WatchEvent"
else:
    print("Error: invalid event type {}.".format(sys.argv[1]))
    sys.exit(1)

def parse_files(filename):
    # Mappings.
    user_id2name = {}
    repo_id2name = {}
    user_repo_edges = []
    print(filename)
    with open(filename, "r") as f:
        lines = f.readlines()
    for line in lines:
        data = json.loads(line)
        if data["type"] == EVENT_TYPE:
            if data["type"] == "MemberEvent" and \
                    data["payload"]["action"] != "added":
                continue
            actor_name = data["actor"]["login"]
            actor_id = str(data["actor"]["id"])
            repo_name = data["repo"]["name"]
            repo_id = data["repo"]["id"]
            if not actor_id in user_id2name:
                user_id2name[actor_id] = actor_name
            if not repo_id in repo_id2name:
                repo_id2name[repo_id] = repo_name
            if data["type"] == "MemberEvent":
                member_name = data["payload"]["member"]["login"]
                member_id = str(data["payload"]["member"]["id"])
                if not member_id in user_id2name:
                    user_id2name[member_id] = member_name
                user_repo_edges.append((member_id, repo_id))
            user_repo_edges.append((actor_id, repo_id))
    return user_id2name, repo_id2name, user_repo_edges

# Collect files.
in_file = sys.argv[2]
if os.path.isdir(in_file):
    files = [os.path.join(in_file, f)
             for f in os.listdir(in_file)
             if os.path.splitext(f)[-1] == ".json"]
else:
    files = [in_file]
print("{} files.".format(len(files)))

# Parsing.
user_id2name = {}
repo_id2name = {}
user_repo_edges = []

if len(sys.argv) == 5:
    N_PROCESS = int(sys.argv[4])
else:
    N_PROCESS = 16
with Pool(processes=N_PROCESS) as pool:
    # result = [(user_id2name, repo_id2name, user_repo_edges), (), ..., ()]
    for result in pool.imap_unordered(parse_files,
                                      files,
                                      len(files)//N_PROCESS):
        user_id2name = {**user_id2name, **result[0]}
        repo_id2name = {**repo_id2name, **result[1]}
        user_repo_edges += result[2]
print("Users: {}".format(len(user_id2name)))
print("Repos: {}".format(len(repo_id2name)))
print("Edges: {}".format(len(user_repo_edges)))

# Save to files.
print("Saving...")
with open("{}.user".format(sys.argv[3]), "wb") as f:
    pickle.dump(user_id2name, f)
with open("{}.repo".format(sys.argv[3]), "wb") as f:
    pickle.dump(repo_id2name, f)
with open("{}.edge".format(sys.argv[3]), "wb") as f:
    pickle.dump(user_repo_edges, f)
