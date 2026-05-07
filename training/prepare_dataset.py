"""
Dataset preparation for Babel fine-tuning.

Downloads CoVoST-2 Hindi→English from HuggingFace, preprocesses audio
into log-mel spectrograms and tokenizes English translations.

Run:
    python prepare_dataset.py

Outputs cached dataset to ./data/ (HF cache) ready for finetune.py.
"""

import logging
import os
import sys

import datasets
import numpy as np
import soundfile as sf
from datasets import load_dataset, DatasetDict, Audio
from transformers import WhisperProcessor

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("babel.prepare")


def load_covost2() -> DatasetDict:
    logger.info(f"Downloading CoVoST-2 {config.DATASET_CONFIG}...")
    # CoVoST-2 requires Common Voice audio — HF will download automatically
    # Note: first download is large (~5-10GB for Hindi). Be patient.
    ds = DatasetDict()
    for split, hf_split in [
        ("train",      config.DATASET_SPLIT_TRAIN),
        ("validation", config.DATASET_SPLIT_VAL),
        ("test",       config.DATASET_SPLIT_TEST),
    ]:
        logger.info(f"  Loading split: {hf_split}")
        subset = load_dataset(
            config.DATASET_NAME,
            config.DATASET_CONFIG,
            split=hf_split,
            trust_remote_code=True,
        )
        if split == "train" and config.MAX_TRAIN_SAMPLES:
            subset = subset.select(range(min(config.MAX_TRAIN_SAMPLES, len(subset))))
        if split == "validation" and config.MAX_VAL_SAMPLES:
            subset = subset.select(range(min(config.MAX_VAL_SAMPLES, len(subset))))
        ds[split] = subset

    logger.info(f"Dataset loaded: {ds}")
    return ds


def prepare_processor() -> WhisperProcessor:
    logger.info(f"Loading processor from {config.BASE_MODEL}")
    processor = WhisperProcessor.from_pretrained(
        config.BASE_MODEL,
        language=config.LANGUAGE,
        task=config.TASK,
    )
    return processor


def preprocess_batch(batch: dict, processor: WhisperProcessor) -> dict:
    """Convert raw audio + translation text into Whisper input features + labels."""
    # CoVoST-2 audio is already at 16kHz (Common Voice format)
    audio = batch["audio"]
    samples = audio["array"]
    sr = audio["sampling_rate"]

    # Safety: resample if not 16kHz (shouldn't happen with HF Audio feature)
    if sr != 16_000:
        import librosa
        samples = librosa.resample(samples, orig_sr=sr, target_sr=16_000)

    # Trim/pad to 30s max (Whisper hard constraint)
    max_samples = int(config.MAX_AUDIO_SECONDS * 16_000)
    if len(samples) > max_samples:
        samples = samples[:max_samples]

    # Extract log-mel features
    input_features = processor.feature_extractor(
        samples, sampling_rate=16_000, return_tensors="np"
    ).input_features[0]

    # Tokenize target text as labels
    target_text = batch.get("transcription") or batch.get("sentence") or batch.get("text", "")
    if isinstance(target_text, dict):
        target_text = target_text.get("en", "")
    else:
        target_text = str(target_text)

    labels = processor.tokenizer(
        target_text,
        max_length=config.MAX_LABEL_TOKENS,
        truncation=True,
    ).input_ids

    return {
        "input_features": input_features,
        "labels": labels,
    }


def main():
    os.makedirs("./data", exist_ok=True)

    processor = prepare_processor()
    raw_ds = load_covost2()

    # Cast audio column to HF Audio for automatic loading
    raw_ds = raw_ds.cast_column("audio", Audio(sampling_rate=16_000))

    logger.info("Preprocessing dataset (this may take 20-60 minutes)...")
    processed = raw_ds.map(
        lambda batch: preprocess_batch(batch, processor),
        remove_columns=raw_ds["train"].column_names,
        num_proc=4,
        desc="Preprocessing",
    )
    processed.set_format("numpy")

    save_path = "./data/fleurs_hi_in"
    processed.save_to_disk(save_path)
    logger.info(f"✅ Dataset saved to {save_path}")
    logger.info(f"   Train: {len(processed['train'])} samples")
    logger.info(f"   Val:   {len(processed['validation'])} samples")
    logger.info(f"   Test:  {len(processed['test'])} samples")


if __name__ == "__main__":
    main()
