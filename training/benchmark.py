"""
Babel — Turbo Benchmark (v5 — Speed + Resumability)

Optimized for:
1. Speed: Greedy decoding (beams=1)
2. Reliability: Periodic checkpointing (saves every 5 batches)
3. Resume support: Automatically skips already-processed samples
"""

import io
import json
import logging
import os
import re
import sys
import unicodedata

# ── UTF-8 stdout ─────────────────────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import evaluate
import torch
from datasets import load_from_disk
from peft import PeftModel
from torch.utils.data import DataLoader
from tqdm import tqdm
from transformers import WhisperForConditionalGeneration, WhisperProcessor

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("babel.turbo")

# ── Turbo configuration ──────────────────────────────────────────────────────
EVAL_SAMPLES   = 100   # Sufficient for portfolio metrics
BATCH_SIZE     = 8     # Optimized for RTX 5060
MAX_NEW_TOKENS = 128   # Standard for FLEURS
NUM_BEAMS      = 1     # TURBO MODE: Greedy decoding
CHECKPOINT_FILE = "eval_checkpoint.json"


# ── Text normalisation & cleanup ──────────────────────────────────────────────
_PUNCT = re.compile(r"[।|॥,\.!?;:\-–—\"\'()\[\]{}]")
_SPACES = re.compile(r"\s+")
_STUTTER = re.compile(r"(.)\1{2,}")

def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _PUNCT.sub(" ", text)
    text = _SPACES.sub(" ", text).strip()
    return text

def clean_output(text: str) -> str:
    text = _STUTTER.sub(r"\1\1", text)
    return text


def collate_fn(batch, dtype):
    features = torch.stack([torch.tensor(b["input_features"]) for b in batch]).to(dtype)
    labels = [b["labels"] for b in batch]
    return features, labels


def run_evaluation(model, processor, dataset, model_key: str, desc: str) -> dict:
    wer_metric = evaluate.load("wer")
    model.eval()
    device = next(model.parameters()).device
    dtype  = next(model.parameters()).dtype

    # Resume logic
    results_store = {"predictions": [], "references": []}
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            full_data = json.load(f)
            if model_key in full_data:
                results_store = full_data[model_key]
                logger.info(f"Resuming {model_key} from checkpoint ({len(results_store['predictions'])} samples done)")

    start_idx = len(results_store["predictions"])
    
    if start_idx < len(dataset):
        remaining_ds = dataset.select(range(start_idx, len(dataset)))
        loader = DataLoader(remaining_ds, batch_size=BATCH_SIZE, collate_fn=lambda b: collate_fn(b, dtype))

        forced_decoder_ids = processor.get_decoder_prompt_ids(language=config.LANGUAGE, task=config.TASK)

        for i, (input_features, batch_labels) in enumerate(tqdm(loader, desc=desc)):
            input_features = input_features.to(device)
            with torch.no_grad():
                pred_ids = model.generate(
                    input_features=input_features,
                    forced_decoder_ids=forced_decoder_ids,
                    max_new_tokens=MAX_NEW_TOKENS,
                    num_beams=NUM_BEAMS,
                    use_cache=True,
                )

            for ids, label_ids in zip(pred_ids, batch_labels):
                label_ids = [l if l != -100 else processor.tokenizer.pad_token_id for l in label_ids]
                p = clean_output(processor.tokenizer.decode(ids, skip_special_tokens=True))
                r = processor.tokenizer.decode(label_ids, skip_special_tokens=True)
                results_store["predictions"].append(p)
                results_store["references"].append(r)

            # Periodic checkpoint save
            if i % 3 == 0:
                full_data = {}
                if os.path.exists(CHECKPOINT_FILE):
                    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
                        full_data = json.load(f)
                full_data[model_key] = results_store
                with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
                    json.dump(full_data, f, ensure_ascii=False)

    # Calculate final WER on normalised text
    preds_norm = [normalise(p) for p in results_store["predictions"]]
    refs_norm  = [normalise(r) for r in results_store["references"]]
    
    # Filter empty refs
    valid = [(p, r) for p, r in zip(preds_norm, refs_norm) if r.strip()]
    if not valid: return {"wer": 1.0, "predictions": [], "references": []}
    
    pn, rn = zip(*valid)
    wer = wer_metric.compute(predictions=list(pn), references=list(rn))
    
    return {
        "wer": round(wer, 4),
        "predictions": results_store["predictions"],
        "references": results_store["references"]
    }


def main():
    if not os.path.exists("./data/fleurs_hi_in"):
        logger.error("Run prepare_dataset.py first.")
        return

    processor = WhisperProcessor.from_pretrained(config.BASE_MODEL, language=config.LANGUAGE, task=config.TASK)
    ds_test = load_from_disk("./data/fleurs_hi_in")["test"].select(range(EVAL_SAMPLES))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype  = torch.float16 if config.FP16 and device == "cuda" else torch.float32

    # 1. Base Model
    logger.info("Step 1/2: Base Model Evaluation")
    base_model = WhisperForConditionalGeneration.from_pretrained(config.BASE_MODEL, torch_dtype=dtype).to(device)
    base_results = run_evaluation(base_model, processor, ds_test, "base", "Base Whisper")
    del base_model
    torch.cuda.empty_cache()

    # 2. Fine-tuned Model
    logger.info("Step 2/2: Fine-tuned Model Evaluation")
    ft_path = os.path.join(config.OUTPUT_DIR, "final")
    if os.path.exists(ft_path):
        ft_base = WhisperForConditionalGeneration.from_pretrained(config.BASE_MODEL, torch_dtype=dtype).to(device)
        ft_model = PeftModel.from_pretrained(ft_base, ft_path)
        ft_results = run_evaluation(ft_model, processor, ds_test, "finetuned", "Babel Fine-tuned")
        del ft_model
        torch.cuda.empty_cache()
    else:
        ft_results = None

    # Final Report
    print("\n" + "="*50)
    print("  BABEL TURBO BENCHMARK RESULTS")
    print("="*50)
    print(f"  Base Whisper WER       : {base_results['wer']:.4f}")
    if ft_results:
        delta = (base_results['wer'] - ft_results['wer']) / base_results['wer'] * 100
        print(f"  Babel Fine-tuned WER   : {ft_results['wer']:.4f} ({delta:+.1f}% improvement)")
    print("="*50)
    
    # Save final results
    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump({"base": base_results, "finetuned": ft_results}, f, ensure_ascii=False, indent=2)
    logger.info("Done! Final results in eval_results.json")

if __name__ == "__main__":
    main()
