#! /usr/bin/env python3

import os
import random
from pathlib import Path
from ultralytics import YOLO
import wandb
from uuid import uuid4
from dotenv import load_dotenv


from pathlib import Path

HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
DATA_YAML = (HERE / "../dataset/dataset.yaml").resolve()


# Load .env and get W&B key
load_dotenv(Path.cwd() / ".env")
wandb_key = os.getenv("WANDB_API_KEY")
if not wandb_key:
    raise ValueError("WANDB_API_KEY not found in .env file!")
os.environ["WANDB_START_METHOD"] = "thread"
wandb.login(key=wandb_key)

model_name = "yolo11m-seg"
# Create W&B run
run_id = str(uuid4())[:8]
run_name = f"{model_name}-{run_id}"
epochs, imgsz, batch, workers = 100, 640, 16, 8

project_name = "pokemon-card-segmentation"

wandb.init(
    project=project_name,
    name=run_name,
    config={
        "epochs": epochs,
        "imgsz": imgsz,
        "batch": batch,
        "workers": workers
    }
)


# Train YOLO model
model = YOLO(f"models/{model_name}.pt")
results = model.train(
    data=str(DATA_YAML),
    epochs=epochs,  
    imgsz=imgsz,
    batch=batch,
    workers=workers,
    device=0,
    save=True,
    save_period=10,
    project=project_name,
    name=run_name,  # match W&B run name
    verbose=True
)
# Save model and end W&B run
model.save(f"models/{model_name}-trained.pt")

os.remove("yolo11n.pt")

wandb.finish()
