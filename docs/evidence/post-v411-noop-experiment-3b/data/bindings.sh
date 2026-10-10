set -eu
cd /tmp/nift-sidecar-experiment/core
make -j2 test-embed test-bindings > /tmp/nift-sidecar-experiment/embed-bindings.txt 2>&1
