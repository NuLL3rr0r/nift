set -eu
p=/tmp/nift-sidecar-experiment
repo=/home/nick/Repositories/nift/nift
cd "$p"
python3 sidecar-21.py > sidecar-21.txt 2>&1
python3 "$repo/tests/dependency_status.py" --nift ./nift-e3b --output status-contracts.json > status-contracts.txt 2>&1
python3 "$repo/tests/dependency_path_identity.py" --nift ./nift-e3b --baseline ./nift-e2 --output path-contracts.json > path-contracts.txt 2>&1
python3 "$repo/tests/consumer_dependency_snapshots.py" --nift ./nift-e3b --output snapshot-contracts.json > snapshot-contracts.txt 2>&1
python3 "$repo/tests/shared_dependency_targeted_reproducer.py" --nift ./nift-e3b --output snapshot-matrix.json --require-clean > snapshot-matrix.txt 2>&1
python3 "$repo/tests/randomized_incremental_differential.py" --nift ./nift-e3b --seeds 0,1,2,3,4,5,6,7,8,9,10,11 --steps 96 --output randomized.json > randomized.txt 2>&1
python3 instrument.py > counters-build.txt 2>&1
gcc -O2 -shared -fPIC alloc.c -o alloc.so
python3 diagnostics.py > diagnostics.txt 2>&1
python3 prepare-core.py > prepare-core.txt 2>&1
cd core
make -j2 all > "$p/full-build.txt" 2>&1
sha256sum nift > "$p/full-build-sha256.txt"
make -j2 test > "$p/regression.txt" 2>&1
make -j2 embed > "$p/embed.txt" 2>&1
NIFT_BIN="$p/nift-e3b" NIFT_EXPECT_VERSION=4.11.0 NIFT_EMBED_PREFIX="$p/core/dist/embed-prefix" bash /home/nick/Repositories/nift/nift-regression-suite/run-contract.sh > "$p/nrs.txt" 2>&1
NIFT_BIN="$p/nift-e3b" bash /home/nick/Repositories/nift/packages-regression-suite/run.sh > "$p/prs.txt" 2>&1
