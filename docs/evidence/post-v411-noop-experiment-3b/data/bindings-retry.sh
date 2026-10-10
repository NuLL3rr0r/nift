set -eu
cd /tmp/nift-sidecar-experiment/core
GOFLAGS="${GOFLAGS:-} -buildvcs=false" make -j2 test-bindings > /tmp/nift-sidecar-experiment/bindings-retry.txt 2>&1
bash tests/build_boundary_candidate.sh > /tmp/nift-sidecar-experiment/build-boundary.txt 2>&1
