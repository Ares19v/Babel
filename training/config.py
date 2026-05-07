"""
Fine-tuning configuration for Babel.

Target: whisper-large-v3 fine-tuned on CoVoST-2 (Hindi→English translation)
using LoRA (PEFT) to fit in 8GB VRAM (RTX 5060).

Why CoVoST-2:
  - 861 hours of speech translation data across 21 language pairs
  - Hindi→English is one of the richest pairs
  - Directly trains the translate task (audio_in → english_text_out)
  - Measurable improvement on low-resource accents vs base Whisper

Why LoRA:
  - Full whisper-large-v3 fine-tune needs ~24GB VRAM — impossible on 8GB
  - LoRA trains <1% of params via rank-decomposed adapter matrices
  - With gradient checkpointing + fp16, fits in ~7GB VRAM
  - Adapter weights are tiny (~50MB) — easy to share and version
"""

# ── Model ──────────────────────────────────────────────────────────────────────
BASE_MODEL = "openai/whisper-large-v3"   # base checkpoint
LANGUAGE   = "hi"                        # source language code
TASK       = "transcribe"                # ASR task: Hindi speech -> Hindi text

# ── Dataset ───────────────────────────────────────────────────────────────────
DATASET_NAME   = "google/fleurs"
DATASET_CONFIG = "hi_in"                 # Hindi
DATASET_SPLIT_TRAIN = "train"
DATASET_SPLIT_VAL   = "validation"
DATASET_SPLIT_TEST  = "test"
MAX_TRAIN_SAMPLES   = 1500               # FLEURS hi_in train size is ~2000
MAX_VAL_SAMPLES     = 200

# ── LoRA hyperparameters ───────────────────────────────────────────────────────
LORA_R          = 32    # rank — higher = more capacity, more VRAM
LORA_ALPHA      = 64    # scaling factor (usually 2×r)
LORA_DROPOUT    = 0.05
LORA_TARGET_MODULES = [
    "q_proj", "v_proj",               # attention projections in decoder
    "k_proj", "out_proj",             # full attention for better quality
    "fc1", "fc2",                     # feed-forward layers
]
LORA_BIAS = "none"

# ── Training hyperparameters ───────────────────────────────────────────────────
OUTPUT_DIR          = "./checkpoints"
LOGGING_DIR         = "./logs"
NUM_TRAIN_EPOCHS    = 3
BATCH_SIZE          = 8       # effective batch (with grad accumulation below)
GRAD_ACCUM_STEPS    = 4       # effective batch = 8 × 4 = 32
LEARNING_RATE       = 1e-4
WARMUP_STEPS        = 100
SAVE_STEPS          = 1000
EVAL_STEPS          = 500
LOGGING_STEPS       = 25
FP16                = True    # mixed precision (RTX 5060 supports fp16)
BF16                = False   # prefer fp16 over bf16 for CTranslate2 compat
GRADIENT_CHECKPOINTING = True # saves ~40% VRAM at cost of ~20% speed
DATALOADER_WORKERS  = 4
MAX_AUDIO_SECONDS   = 30.0    # Whisper's hard cap
MAX_LABEL_TOKENS    = 440

# ── Evaluation ────────────────────────────────────────────────────────────────
METRIC = "wer"       # Word Error Rate — lower is better
PUSH_TO_HUB = False  # set True + HF_TOKEN env var to publish on HuggingFace
HUB_MODEL_ID = "babel-whisper-hi-en"
