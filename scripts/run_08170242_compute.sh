#!/usr/bin/env bash
set -uo pipefail

family=$1
label=$2
root=/share/org/YZWL/yzwl_yuanzh/work/kimi-work/bio-mystery-synth
resource=/share/org/YZWL/yzwl_yuanzh/work/kimi-work/resource

cd "$root"
source /share/apps/anaconda3/bin/activate
conda activate bio-mystery-synth
export PROTO_HOME="$resource/proto_home"
export PROTO_MODEL_CACHE="$resource/proto_model_cache"
export PROTO_ESMFOLD_STANDALONE_DIR="$root/proto_standalone/esmfold"
export HF_HOME="$resource/proto_model_cache/huggingface"
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1

python scripts/08170242_generate.py "$family" > "Log/08170242/$label.log" 2>&1
status=$?
printf '%s\n' "$status" > "Log/08170242/$label.exit"
exit "$status"
