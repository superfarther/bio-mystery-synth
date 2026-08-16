#!/bin/bash
# Setup script for ESMFold standalone environment
set -euo pipefail
source standalone_helpers.sh

echo "Setting up ESMFold standalone environment..."

export DETECTED_COMPUTE_PLATFORM=cuda
export DETECTED_DRIVER_VERSION=570
export DETECTED_CUDA_VERSION=12
export RECOMMENDED_TORCH_SPEC='torch>=2.8,<3'
export RECOMMENDED_TORCH_INDEX=https://download.pytorch.org/whl/cu128
export TORCH_CUDA_ARCH_LIST=9.0

echo "Installing uv package manager..."
pip install -i https://mirrors.cloud.tencent.com/pypi/simple uv

proto_install_pytorch

echo "Installing remaining dependencies..."
uv pip install --index https://mirrors.cloud.tencent.com/pypi/simple transformers==5.12.1 biopython

echo "ESMFold setup complete!"
