#!/bin/bash
# CI setup script for k3etcd
# Creates Docker network and pulls etcd image for tests

set -e

# Create Docker network with specific subnet for etcd tests
docker network create --subnet=192.168.52.0/24 etcd-test-net || true

# Pull etcd image
docker pull quay.io/coreos/etcd:v3.5.0
