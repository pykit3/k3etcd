#!/bin/bash
# CI setup script for k3etcd
# Pre-pulls etcd image for tests (k3utdocker handles network creation)

set -e

# Pull etcd image to avoid timeout during tests
docker pull quay.io/coreos/etcd:v3.5.0
