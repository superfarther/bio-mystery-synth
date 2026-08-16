#!/usr/bin/env bash
set -o pipefail

cd /share/org/YZWL/yzwl_yuanzh/work/kimi-work/bio-mystery-synth || exit 1
source /share/apps/anaconda3/bin/activate
conda activate bio-mystery-synth
export PYTHONPATH="/share/org/YZWL/yzwl_yuanzh/work/kimi-work/proto-language:/share/org/YZWL/yzwl_yuanzh/work/kimi-work/proto-tools:${PYTHONPATH:-}"
export PROTO_MODEL_CACHE=/share/org/YZWL/yzwl_yuanzh/work/kimi-work/resource/proto_model_cache
export HF_HOME=/share/org/YZWL/yzwl_yuanzh/work/kimi-work/resource/proto_model_cache/huggingface
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export CUDA_VISIBLE_DEVICES="${CUDA_VISIBLE_DEVICES:-1}"

python scripts/08161746_gpu.py 2>&1 | tee Log/08161746/gpu_generation.log
status=${PIPESTATUS[0]}
printf '%s\n' "$status" > Log/08161746/gpu_generation.exit
exit "$status"
