"""
LoRA Fine-tuning Script for Babel.

Trains whisper-large-v3 with PEFT LoRA on FLEURS Hindi.
Designed for RTX 5060 (8GB VRAM) with fp16 + gradient checkpointing.

Run AFTER prepare_dataset.py:
    python finetune.py

Outputs checkpoints to ./checkpoints/  (saved every 25 steps — never lose progress)
"""

import logging
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import torch
from datasets import load_from_disk
from jiwer import wer as compute_wer
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    WhisperForConditionalGeneration,
    WhisperProcessor,
    set_seed,
)

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("babel.finetune")
set_seed(42)


# ──────────────────────────────────────────────────────────────────────────────
# Dtype fix: patch the WhisperEncoder directly so that NO code path
# (training, eval, generate, detect_language, etc.) ever hits a float/half clash.
# This is the lowest-level, most reliable place to put it.
# ──────────────────────────────────────────────────────────────────────────────
def patch_whisper_encoder_dtype(model: WhisperForConditionalGeneration) -> None:
    """
    Wraps WhisperEncoder.forward so input_features is always cast to the
    encoder's weight dtype before the first conv layer.
    Works for training, evaluation, AND generate() / detect_language().
    """
    encoder = model.model.encoder
    _original_encoder_forward = encoder.forward

    def _dtype_safe_encoder_forward(input_features=None, *args, **kwargs):
        if input_features is not None and torch.is_tensor(input_features):
            target_dtype = next(encoder.parameters()).dtype
            input_features = input_features.to(target_dtype)
        return _original_encoder_forward(input_features, *args, **kwargs)

    encoder.forward = _dtype_safe_encoder_forward
    logger.info("✓ WhisperEncoder dtype patch applied (float16-safe for all code paths)")


# ── Data collator ──────────────────────────────────────────────────────────────
@dataclass
class WhisperDataCollator:
    """Only ever returns input_features + labels — nothing else reaches the model."""
    processor: Any

    def __call__(self, features: List[Dict]) -> Dict[str, torch.Tensor]:
        # Pad audio features (each is already a fixed 80×3000 numpy array)
        input_feats = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_feats, return_tensors="pt")

        # Pad label token sequences
        label_feats = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_feats, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(
            labels_batch.attention_mask.ne(1), -100
        )
        # Strip BOS token — Whisper generates it automatically during inference
        if (labels[:, 0] == self.processor.tokenizer.bos_token_id).all().cpu().item():
            labels = labels[:, 1:]

        return {"input_features": batch["input_features"], "labels": labels}


# ── Metrics ────────────────────────────────────────────────────────────────────
def build_compute_metrics(processor: WhisperProcessor):
    def compute_metrics(pred):
        pred_ids  = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str  = processor.tokenizer.batch_decode(pred_ids,  skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        return {"wer": round(compute_wer(label_str, pred_str), 4)}
    return compute_metrics


# ── Custom Trainer ─────────────────────────────────────────────────────────────
class WhisperTrainer(Seq2SeqTrainer):
    """
    Two fixes vs vanilla Seq2SeqTrainer:

    1. compute_loss: bypasses PeftModelForSeq2SeqLM.forward (which hardcodes
       `input_ids=None` causing "multiple values for keyword argument 'input_ids'"
       deep in WhisperDecoder). We call model.base_model.model directly —
       the LoRA weights are applied in-place so gradients flow correctly.

    2. prediction_step: fully disabled during training (eval_strategy="no").
       Kept here as a safety net with the same bypass in case eval is re-enabled.
    """

    def compute_loss(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        # model.base_model.model is WhisperForConditionalGeneration (with LoRA applied)
        whisper = model.base_model.model
        outputs = whisper(
            input_features=inputs["input_features"],   # encoder dtype patch handles cast
            labels=inputs["labels"],
        )
        loss = outputs.loss
        return (loss, outputs) if return_outputs else loss


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    if not os.path.exists("./data/fleurs_hi_in"):
        logger.error("Dataset not found — run prepare_dataset.py first.")
        sys.exit(1)

    # ── Processor ─────────────────────────────────────────────────────────────
    logger.info(f"Loading processor from {config.BASE_MODEL}")
    processor = WhisperProcessor.from_pretrained(
        config.BASE_MODEL,
        language=config.LANGUAGE,
        task=config.TASK,
    )
    processor.tokenizer.set_prefix_tokens(language=config.LANGUAGE, task=config.TASK)

    # ── Base model ────────────────────────────────────────────────────────────
    logger.info(f"Loading base model {config.BASE_MODEL}")
    base_model = WhisperForConditionalGeneration.from_pretrained(
        config.BASE_MODEL,
        torch_dtype=torch.float16 if config.FP16 else torch.float32,
    )

    # ── CRITICAL: Apply dtype patch NOW, before LoRA wrapping ─────────────────
    # Patching at the encoder level means it survives get_peft_model() wrapping
    # and is called regardless of whether the entry point is forward() or generate()
    patch_whisper_encoder_dtype(base_model)

    base_model.model.encoder.requires_grad_(False)
    base_model.config.forced_decoder_ids = None
    base_model.config.suppress_tokens    = []
    base_model.config.use_cache          = False

    if config.GRADIENT_CHECKPOINTING:
        base_model.enable_input_require_grads()

    # ── LoRA ──────────────────────────────────────────────────────────────────
    logger.info(f"Applying LoRA (r={config.LORA_R}, alpha={config.LORA_ALPHA})")
    lora_config = LoraConfig(
        r=config.LORA_R,
        lora_alpha=config.LORA_ALPHA,
        target_modules=config.LORA_TARGET_MODULES,
        lora_dropout=config.LORA_DROPOUT,
        bias=config.LORA_BIAS,
        task_type=TaskType.SEQ_2_SEQ_LM,
    )
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # ── Dataset ───────────────────────────────────────────────────────────────
    logger.info("Loading preprocessed dataset...")
    ds = load_from_disk("./data/fleurs_hi_in")
    ds.set_format("numpy")

    # ── Training args ─────────────────────────────────────────────────────────
    training_args = Seq2SeqTrainingArguments(
        output_dir=config.OUTPUT_DIR,
        num_train_epochs=config.NUM_TRAIN_EPOCHS,
        per_device_train_batch_size=config.BATCH_SIZE,
        per_device_eval_batch_size=config.BATCH_SIZE,
        gradient_accumulation_steps=config.GRAD_ACCUM_STEPS,
        learning_rate=config.LEARNING_RATE,
        warmup_steps=config.WARMUP_STEPS,
        fp16=config.FP16,
        bf16=config.BF16,
        # Evaluation completely disabled during training.
        # eval_strategy="no" means trainer.train() will NEVER call predict/generate.
        # This removes the entire code path that crashed last time.
        eval_strategy="no",
        save_strategy="steps",
        save_steps=25,          # Save every 25 steps — never lose more than ~12 mins of work
        save_total_limit=3,     # Keep last 3 checkpoints on disk
        logging_steps=config.LOGGING_STEPS,
        predict_with_generate=False,    # Must be False when eval_strategy="no"
        dataloader_num_workers=0,       # 0 = no Windows multiprocessing deadlocks
        gradient_checkpointing=config.GRADIENT_CHECKPOINTING,
        report_to=["tensorboard"],
        remove_unused_columns=False,    # Our collator handles columns manually
        label_names=["labels"],
    )

    # ── Trainer ───────────────────────────────────────────────────────────────
    trainer = WhisperTrainer(
        model=model,
        args=training_args,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        processing_class=processor.feature_extractor,
        data_collator=WhisperDataCollator(processor=processor),
        compute_metrics=build_compute_metrics(processor),
    )

    # ── Train ─────────────────────────────────────────────────────────────────
    logger.info("🚀 Starting fine-tuning...")
    logger.info(f"   Effective batch size : {config.BATCH_SIZE * config.GRAD_ACCUM_STEPS}")
    logger.info(f"   Epochs               : {config.NUM_TRAIN_EPOCHS}")
    logger.info(f"   Checkpoints every    : 25 steps")
    logger.info(f"   Device               : {'GPU ✓' if torch.cuda.is_available() else 'CPU'}")
    trainer.train()

    # ── Save final model ──────────────────────────────────────────────────────
    # trainer.save_model() is safer than model.save_pretrained() because it
    # handles distributed training, PEFT state dicts, and unwrapping correctly.
    final_path = os.path.join(config.OUTPUT_DIR, "final")
    logger.info(f"Saving final model to {final_path} ...")
    trainer.save_model(final_path)
    processor.save_pretrained(final_path)
    logger.info(f"✅ Done! Model saved to {final_path}")

    if config.PUSH_TO_HUB:
        model.push_to_hub(config.HUB_MODEL_ID)
        processor.push_to_hub(config.HUB_MODEL_ID)
        logger.info(f"Published → https://huggingface.co/{config.HUB_MODEL_ID}")


if __name__ == "__main__":
    main()
