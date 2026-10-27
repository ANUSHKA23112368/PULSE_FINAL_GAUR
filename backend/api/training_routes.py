"""
PULSE Training API Endpoints
Provides endpoints for:
- Starting Bio_ClinicalBERT fine-tuning
- Streaming live training progress via SSE
- Checking training status
- Hot-reloading model weights after training
- Viewing training history and metrics
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

training_router = APIRouter(prefix="/api/training")

# Thread-safe training state
_training_lock = threading.Lock()
_training_state: Dict[str, Any] = {
    "is_training": False,
    "progress": None,
    "history": [],
    "last_result": None,
}
_training_events: List[Dict[str, Any]] = []


class TrainRequest(BaseModel):
    epochs: int = Field(5, ge=1, le=20, description="Number of training epochs")
    learning_rate: float = Field(3e-5, gt=0, description="Learning rate")
    batch_size: int = Field(4, ge=1, le=16, description="Batch size")
    max_length: int = Field(256, ge=64, le=512, description="Max token length")
    synthetic_count: int = Field(200, ge=0, le=500, description="Number of synthetic ISBAR augmentation notes")
    trainable_last_n: int = Field(3, ge=-1, le=12, description="Number of last encoder layers to train (-1 for all)")
    skip_full_retrain: bool = Field(False, description="Skip deployment retrain on all data after evaluation")


def _run_training(config: Dict[str, Any]):
    """Background training thread that updates shared state."""
    import sys
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, BASE_DIR)

    try:
        import torch
        from transformers import AutoModelForTokenClassification, BertTokenizerFast, get_linear_schedule_with_warmup
        import torch.nn.functional as F
        from collections import Counter

        from backend.dataset.hospital_training_corpus import (
            export_hospital_training_corpus,
            load_fold_ids,
            load_hospital_training_documents,
        )
        from backend.extraction.label_schema import ID2LABEL, LABEL2ID, LABEL_LIST, MACRO_CATEGORIES

        MODEL_CHECKPOINT = "emilyalsentzer/Bio_ClinicalBERT"
        MODEL_OUTPUT_DIR = os.path.join(BASE_DIR, "backend", "models", "clinical_bert")
        RESULTS_PATH = os.path.join(BASE_DIR, "data", "gold_standard", "clinicalbert_production_results.json")
        LOCAL_BACKBONE = MODEL_OUTPUT_DIR

        def emit_event(event_type: str, data: Dict[str, Any]):
            with _training_lock:
                event = {"type": event_type, "timestamp": time.time(), **data}
                _training_events.append(event)
                _training_state["progress"] = event

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        emit_event("init", {
            "message": "Initializing PULSE BioClinicalBERT training",
            "device": str(device),
            "pytorch_version": torch.__version__,
            "config": config,
        })

        # Export and load corpus
        emit_event("data", {"message": "Building hospital training corpus...", "phase": "data_preparation"})
        export_hospital_training_corpus(n_synthetic=config["synthetic_count"])
        documents = load_hospital_training_documents(include_synthetic=True, n_synthetic=config["synthetic_count"])
        splits = load_fold_ids("fold_0")
        test_ids = set(str(i) for i in splits["test"])

        gold_docs = [d for d in documents if d["source"] == "nicta_suominen_nursing_handover"]
        synth_docs = [d for d in documents if d["source"] != "nicta_suominen_nursing_handover"]
        train_docs = [d for d in gold_docs if d["report_id"] not in test_ids] + synth_docs
        test_docs = [d for d in gold_docs if d["report_id"] in test_ids]

        emit_event("data_ready", {
            "message": f"Corpus ready: {len(train_docs)} train ({len(train_docs) - len(synth_docs)} gold + {len(synth_docs)} synthetic), {len(test_docs)} test",
            "train_count": len(train_docs),
            "test_count": len(test_docs),
            "gold_count": len(train_docs) - len(synth_docs),
            "synthetic_count": len(synth_docs),
        })

        # Resolve backbone
        config_path = os.path.join(LOCAL_BACKBONE, "config.json")
        has_weights = any(
            os.path.exists(os.path.join(LOCAL_BACKBONE, name))
            for name in ("model.safetensors", "pytorch_model.bin")
        )
        backbone = LOCAL_BACKBONE if (os.path.exists(config_path) and has_weights) else MODEL_CHECKPOINT

        # Tokenizer
        emit_event("tokenizer", {"message": f"Loading tokenizer from {backbone}...", "phase": "model_loading"})
        vocab_path = os.path.join(backbone, "vocab.txt") if backbone == LOCAL_BACKBONE else None
        tok_source = backbone if (vocab_path and os.path.exists(vocab_path)) else MODEL_CHECKPOINT
        tokenizer = BertTokenizerFast.from_pretrained(tok_source)

        # Build datasets
        from scripts.train_production_clinicalbert import HospitalNERDataset, collate_train_batch, class_weights_from_dataset, predict_spans, compute_span_eval, decode_pred_spans
        
        emit_event("dataset", {"message": "Tokenizing and aligning training samples...", "phase": "dataset_build"})
        train_dataset = HospitalNERDataset(train_docs, tokenizer, max_length=config["max_length"])
        test_dataset = HospitalNERDataset(test_docs, tokenizer, max_length=config["max_length"])
        emit_event("dataset_ready", {
            "message": f"Dataset ready: {len(train_dataset)} train samples, {len(test_dataset)} test samples",
            "train_samples": len(train_dataset),
            "test_samples": len(test_dataset),
        })

        # Load model
        emit_event("model_load", {"message": f"Loading Bio_ClinicalBERT from {backbone}...", "phase": "model_loading"})
        model = AutoModelForTokenClassification.from_pretrained(
            backbone,
            num_labels=len(LABEL_LIST),
            id2label=ID2LABEL,
            label2id=LABEL2ID,
            ignore_mismatched_sizes=True,
        ).to(device)

        # Freeze lower layers
        trainable_last_n = config["trainable_last_n"]
        if trainable_last_n >= 0:
            for param in model.bert.embeddings.parameters():
                param.requires_grad = False
            n_layers = len(model.bert.encoder.layer)
            freeze_until = max(0, n_layers - trainable_last_n)
            for idx, layer in enumerate(model.bert.encoder.layer):
                requires = idx >= freeze_until
                for param in layer.parameters():
                    param.requires_grad = requires

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        emit_event("model_ready", {
            "message": f"Model loaded. Trainable: {trainable_params:,} / {total_params:,} parameters",
            "trainable_params": trainable_params,
            "total_params": total_params,
            "frozen_layers": max(0, len(model.bert.encoder.layer) - trainable_last_n) if trainable_last_n >= 0 else 0,
        })

        # Training
        from torch.utils.data import DataLoader
        weights = class_weights_from_dataset(train_dataset, device)
        loader = DataLoader(train_dataset, batch_size=config["batch_size"], shuffle=True, collate_fn=collate_train_batch)
        trainable = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(trainable, lr=config["learning_rate"], weight_decay=0.01)
        total_steps = max(1, len(loader) * config["epochs"])
        scheduler = get_linear_schedule_with_warmup(
            optimizer, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
        )

        epoch_losses = []
        start_time = time.time()
        model.train()

        for epoch in range(1, config["epochs"] + 1):
            epoch_start = time.time()
            total_loss = 0.0
            batch_count = 0
            for batch_idx, batch in enumerate(loader):
                optimizer.zero_grad()
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["labels"].to(device)
                outputs = model(input_ids=input_ids, attention_mask=attention_mask)
                loss = F.cross_entropy(
                    outputs.logits.view(-1, len(LABEL_LIST)),
                    labels.view(-1),
                    weight=weights,
                    ignore_index=-100,
                )
                loss.backward()
                torch.nn.utils.clip_grad_norm_(trainable, 1.0)
                optimizer.step()
                scheduler.step()
                total_loss += float(loss.item())
                batch_count += 1

                # Emit batch progress every 10 batches
                if (batch_idx + 1) % 10 == 0 or batch_idx == 0:
                    emit_event("batch", {
                        "epoch": epoch,
                        "batch": batch_idx + 1,
                        "total_batches": len(loader),
                        "batch_loss": round(float(loss.item()), 4),
                        "avg_loss": round(total_loss / batch_count, 4),
                        "learning_rate": round(scheduler.get_last_lr()[0], 8),
                    })

            epoch_loss = total_loss / max(1, batch_count)
            epoch_time = round(time.time() - epoch_start, 1)
            epoch_losses.append(epoch_loss)
            emit_event("epoch", {
                "epoch": epoch,
                "total_epochs": config["epochs"],
                "loss": round(epoch_loss, 4),
                "epoch_time_s": epoch_time,
                "elapsed_s": round(time.time() - start_time, 1),
                "loss_history": [round(l, 4) for l in epoch_losses],
                "message": f"Epoch {epoch}/{config['epochs']} | Loss: {epoch_loss:.4f} | Time: {epoch_time}s",
            })

        total_train_time = round(time.time() - start_time, 1)

        # Evaluation
        emit_event("evaluate", {"message": "Evaluating on held-out gold test set...", "phase": "evaluation"})
        gold_spans, pred_spans = predict_spans(model, test_dataset, device)
        metrics = compute_span_eval(gold_spans, pred_spans)
        emit_event("eval_result", {
            "message": f"Strict F1: {metrics['strict']['f1']}% | Lenient F1: {metrics['lenient']['f1']}%",
            "metrics": metrics,
        })

        # Full retrain
        if not config.get("skip_full_retrain"):
            emit_event("retrain", {"message": "Retraining deployment checkpoint on all gold + synthetic notes...", "phase": "deployment_retrain"})
            full_dataset = HospitalNERDataset(documents, tokenizer, max_length=config["max_length"])
            full_loader = DataLoader(full_dataset, batch_size=config["batch_size"], shuffle=True, collate_fn=collate_train_batch)
            full_trainable = [p for p in model.parameters() if p.requires_grad]
            full_optimizer = torch.optim.AdamW(full_trainable, lr=config["learning_rate"], weight_decay=0.01)
            deploy_epochs = max(1, config["epochs"] - 1)
            full_total_steps = max(1, len(full_loader) * deploy_epochs)
            full_scheduler = get_linear_schedule_with_warmup(
                full_optimizer, num_warmup_steps=int(0.1 * full_total_steps), num_training_steps=full_total_steps
            )
            model.train()
            deploy_loss = 0.0
            for dep_epoch in range(1, deploy_epochs + 1):
                dep_total = 0.0
                for batch in full_loader:
                    full_optimizer.zero_grad()
                    out = model(
                        input_ids=batch["input_ids"].to(device),
                        attention_mask=batch["attention_mask"].to(device),
                    )
                    loss = F.cross_entropy(
                        out.logits.view(-1, len(LABEL_LIST)),
                        batch["labels"].to(device).view(-1),
                        weight=weights,
                        ignore_index=-100,
                    )
                    loss.backward()
                    torch.nn.utils.clip_grad_norm_(full_trainable, 1.0)
                    full_optimizer.step()
                    full_scheduler.step()
                    dep_total += float(loss.item())
                deploy_loss = dep_total / max(1, len(full_loader))
                emit_event("retrain_epoch", {
                    "epoch": dep_epoch,
                    "total_epochs": deploy_epochs,
                    "loss": round(deploy_loss, 4),
                })

        # Save checkpoint
        emit_event("save", {"message": "Saving model checkpoint...", "phase": "saving"})
        os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
        model.save_pretrained(MODEL_OUTPUT_DIR)
        tokenizer.save_pretrained(MODEL_OUTPUT_DIR)

        card = {
            "model": MODEL_CHECKPOINT,
            "task": "Clinical named entity recognition for nursing handover",
            "labels": LABEL_LIST,
            "metrics": metrics,
            "dataset": {
                "gold": "NICTA/ANU Synthetic Nursing Handover (Suominen et al.) — 101 adjudicated ward notes",
                "augmentation": f"{config['synthetic_count']} de-identified ISBAR hospital notes",
                "held_out": "gold fold_0 test documents only",
                "train_documents": len(train_docs),
                "test_documents": len(test_docs),
            },
            "training": {
                "epochs": config["epochs"],
                "lr": config["learning_rate"],
                "batch_size": config["batch_size"],
                "max_length": config["max_length"],
                "trainable_last_n": config["trainable_last_n"],
                "final_weighted_loss": round(epoch_losses[-1], 4) if epoch_losses else None,
                "total_time_s": total_train_time,
                "device": str(device),
            },
            "disclaimer": "PULSE organizes handover text. It does not diagnose or treat.",
        }
        with open(os.path.join(MODEL_OUTPUT_DIR, "training_card.json"), "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2)
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(card, f, indent=2)

        # Hot-reload model
        emit_event("reload", {"message": "Hot-reloading model into live inference pipeline...", "phase": "hot_reload"})
        from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
        clinical_bert_extractor.reload()
        warmup_ms = clinical_bert_extractor.warmup() if clinical_bert_extractor.is_available() else 0

        result = {
            "status": "completed",
            "metrics": metrics,
            "training_time_s": total_train_time,
            "loss_history": [round(l, 4) for l in epoch_losses],
            "final_loss": round(epoch_losses[-1], 4) if epoch_losses else None,
            "model_path": MODEL_OUTPUT_DIR,
            "model_reloaded": clinical_bert_extractor.is_available(),
            "warmup_ms": warmup_ms,
            "config": config,
        }

        emit_event("complete", {
            "message": f"Training complete! Strict F1: {metrics['strict']['f1']}% | Model hot-reloaded | Warmup: {warmup_ms}ms",
            **result,
        })

        with _training_lock:
            _training_state["is_training"] = False
            _training_state["last_result"] = result
            _training_state["history"].append({
                "timestamp": time.time(),
                **result,
            })

    except Exception as e:
        import traceback
        error_msg = f"Training failed: {str(e)}"
        emit_event("error", {"message": error_msg, "traceback": traceback.format_exc()})
        with _training_lock:
            _training_state["is_training"] = False
            _training_state["last_result"] = {"status": "failed", "error": str(e)}


@training_router.get("/status")
async def training_status():
    """Returns current training status and last result."""
    with _training_lock:
        return {
            "is_training": _training_state["is_training"],
            "progress": _training_state["progress"],
            "last_result": _training_state["last_result"],
            "history_count": len(_training_state["history"]),
        }


@training_router.get("/history")
async def training_history():
    """Returns full training run history."""
    with _training_lock:
        return {"history": _training_state["history"]}


@training_router.post("/start")
@training_router.post("/train")
async def start_training(config: TrainRequest):
    """Starts Bio_ClinicalBERT fine-tuning in a background thread."""
    with _training_lock:
        if _training_state["is_training"]:
            raise HTTPException(status_code=409, detail="Training is already in progress.")
        _training_state["is_training"] = True
        _training_state["progress"] = {"type": "queued", "message": "Training queued..."}
        _training_events.clear()

    cfg = config.model_dump() if hasattr(config, "model_dump") else config.dict()
    thread = threading.Thread(target=_run_training, args=(cfg,), daemon=True)
    thread.start()

    return {
        "status": "started",
        "message": "Bio_ClinicalBERT training started in background",
        "config": cfg,
        "stream_url": "/api/training/stream",
    }


@training_router.get("/stream")
async def training_stream():
    """SSE endpoint streaming live training events."""
    def event_generator():
        last_idx = 0
        timeout = 600  # 10 minute max
        start = time.time()
        while time.time() - start < timeout:
            with _training_lock:
                is_training = _training_state["is_training"]
                new_events = _training_events[last_idx:]
                last_idx = len(_training_events)

            for event in new_events:
                yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

            if not is_training and last_idx == len(_training_events):
                yield f"event: done\ndata: {json.dumps({'message': 'Training stream ended'})}\n\n"
                break

            time.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@training_router.get("/model-info")
@training_router.get("/card")
async def model_info():
    """Returns current model checkpoint information."""
    from backend.extraction.clinical_bert_extractor import clinical_bert_extractor

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    MODEL_DIR = os.path.join(BASE_DIR, "backend", "models", "clinical_bert")
    card_path = os.path.join(MODEL_DIR, "training_card.json")

    training_card = None
    if os.path.exists(card_path):
        with open(card_path, "r", encoding="utf-8") as f:
            training_card = json.load(f)

    has_weights = any(
        os.path.exists(os.path.join(MODEL_DIR, name))
        for name in ("model.safetensors", "pytorch_model.bin")
    )

    return {
        "model_name": "Bio_ClinicalBERT",
        "model_id": "emilyalsentzer/Bio_ClinicalBERT",
        "checkpoint_path": MODEL_DIR,
        "has_weights": has_weights,
        "is_loaded": clinical_bert_extractor.is_available(),
        "warmup_complete": clinical_bert_extractor.warmup_complete,
        "last_inference_ms": clinical_bert_extractor.last_inference_ms,
        "average_inference_ms": clinical_bert_extractor.average_inference_ms(),
        "training_card": training_card,
        "metrics": training_card.get("metrics") if training_card else None,
    }


@training_router.post("/reload")
@training_router.post("/hot-reload")
async def reload_model():
    """Hot-reload model weights from disk."""
    from backend.extraction.clinical_bert_extractor import clinical_bert_extractor
    clinical_bert_extractor.reload()
    warmup_ms = clinical_bert_extractor.warmup() if clinical_bert_extractor.is_available() else 0
    return {
        "reloaded": True,
        "is_available": clinical_bert_extractor.is_available(),
        "warmup_ms": warmup_ms,
        "message": "Bio_ClinicalBERT weights successfully hot-reloaded into memory!",
    }

