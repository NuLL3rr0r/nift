set -eu
p=/tmp/nift-sidecar-experiment
cd "$p/core"
make -j2 test > "$p/regression-retry.txt" 2>&1
make -j2 embed > "$p/embed.txt" 2>&1
NIFT_BIN="$p/nift-e3b" NIFT_EXPECT_VERSION=4.11.0 NIFT_EMBED_PREFIX="$p/core/dist/embed-prefix" bash /home/nick/Repositories/nift/nift-regression-suite/run-contract.sh > "$p/nrs.txt" 2>&1
NIFT_BIN="$p/nift-e3b" NIFT_EXPECT_VERSION=4.11.0 bash /home/nick/Repositories/nift/packages-regression-suite/run.sh > "$p/prs.txt" 2>&1
python3 scripts/checkpoint10_cross_platform.py --nift "$p/nift-e3b" --output "$p/linux-checkpoint.json" > "$p/linux-checkpoint.txt" 2>&1
cp "$p/existing-mutations-template.py" scripts/consumer_snapshot_mutations.py
python3 scripts/consumer_snapshot_mutations.py --output "$p/existing-mutations.json" > "$p/existing-mutations.txt" 2>&1
python3 "$p/mutations.py" > "$p/mutations.txt" 2>&1
python3 "$p/sanitizers.py" > "$p/sanitizers.txt" 2>&1
