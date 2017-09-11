import os
import pickle
import sys

# Check arguments.
if len(sys.argv) < 3:
    print("Error: missing arguments.")
    print("Usage: mergedata.py <input-data-dir> <output-data-basename>")
    sys.exit(1)


# Load data.
print("Loading...")
files = [os.path.join(sys.argv[1], f) for f in os.listdir(sys.argv[1]) if f.startswith("2016")]
print("{} files.".format(len(files)))
user_id2name = {}
repo_id2name = {}
user_repo_edges = []
for filename in files:
    print(filename)
    with open(filename, "rb") as f:
        data = pickle.load(f)
        if filename.endswith("user"):
            user_id2name = {**user_id2name, **data}
        elif filename.endswith("repo"):
            repo_id2name = {**repo_id2name, **data}
        elif filename.endswith("edge"):
            user_repo_edges.extend(data)
        else:
            print("Error: unknown input file {}.".format(filename))
print("users = {}, repos = {}, edges = {}"\
        .format(len(user_id2name), len(repo_id2name), len(user_repo_edges)))

# Save to files.
print("Saving...")
with open("{}.user".format(sys.argv[2]), "wb") as f:
    pickle.dump(user_id2name, f)
with open("{}.repo".format(sys.argv[2]), "wb") as f:
    pickle.dump(repo_id2name, f)
with open("{}.edge".format(sys.argv[2]), "wb") as f:
    pickle.dump(user_repo_edges, f)
