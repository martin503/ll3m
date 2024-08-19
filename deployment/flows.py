import os
import re
import sys

import mlflow
from loguru import logger
from prefect import flow
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from deployment.configs import Eval, Model, Monitor, Train
from deployment.utils import main_eval, main_train, update_model_tag


@flow(name="train")
def train(cfg: Train):
    if cfg.suf:
        sys.argv.append(f"--config-name=train_{cfg.suf}.yaml")
    sys.argv.append(
        f"+experiment={cfg.experiment}"
    )  # hack to remove after compose api gets better
    main_train()


@flow(name="eval")
def eval(cfg: Eval):
    # Remove any part of the path before 'mlruns' using regex
    ckpt_path = re.sub(r"^.*?(mlruns)", r"\1", cfg.path)
    # Verify that the modified path starts with 'mlruns'
    if not ckpt_path.startswith("mlruns"):
        raise ValueError(f"Invalid checkpoint path: {ckpt_path}. Path should start with 'mlruns'.")
    if cfg.suf:
        sys.argv.append(f"--config-name=eval_{cfg.suf}.yaml")
    sys.argv.append(f"+ckpt_path=/{ckpt_path}")  # hack to remove after compose api gets better
    main_eval()


@flow(name="promote")
def promote(model: Model):
    client = mlflow.tracking.MlflowClient()
    new_model = update_model_tag(client, model.name, model.version, "staging", "prod")

    try:
        champ = client.get_model_version_by_alias(model.name, "champ")
    except mlflow.exceptions.RestException as e:
        if e.json.get("message") == "Registered model alias champ not found.":
            client.set_registered_model_alias(model.name, "champ", new_model.version)
            return

    champ_metric = client.get_run(champ.run_id).data.metrics.get("test/acc")
    model_metric = client.get_run(new_model.run_id).data.metrics.get("test/acc")
    if model_metric > champ_metric:
        client.delete_registered_model_alias(model.name, "champ")
        client.set_registered_model_alias(model.name, "champ", new_model.version)


@flow(name="archive")
def archive(model: Model):
    client = mlflow.tracking.MlflowClient()
    update_model_tag(client, model.name, model.version, "prod", "archive")


@flow(name="release")
def release(name: str):
    client = mlflow.tracking.MlflowClient()

    best_acc = 0
    registered_models = client.search_registered_models(f"name = '{name}'")
    for model in registered_models:
        versions = client.search_model_versions(f"name='{model.name}'")
        for version in versions:
            if version.tags.get("stage") == "staging":
                update_model_tag(client, name, version.version, "staging", "prod")
                run = client.get_run(version.run_id)
                acc = run.data.metrics.get("test/acc")
                if acc > best_acc:
                    best_acc = acc
                    best_model_in_staging = version
            elif version.tags.get("stage") == "prod":
                update_model_tag(client, name, version.version, "prod", "archive")

    if best_model_in_staging:
        client.delete_registered_model_alias(model.name, "champ")
        client.set_registered_model_alias(model.name, "champ", best_model_in_staging.version)

    logger.info("Model stage updates completed")


@flow(name="monitor")
def monitor(cfg: Monitor):
    client = mlflow.tracking.MlflowClient()
    registry = CollectorRegistry()
    accuracy_metric = Gauge("model_accuracy", "Accuracy of the model", registry=registry)
    loss_metric = Gauge("model_loss", "Loss of the model", registry=registry)
    creation_timestamp_metric = Gauge(
        "creation_timestamp", "Model Creation Timestamp", registry=registry
    )
    version_metric = Gauge("version", "Model version", registry=registry)

    # Get the model version by alias
    model_alias = "champ"
    model_version = client.get_model_version_by_alias(name=cfg.name, alias=model_alias)
    if not model_version:
        raise ValueError(f"No model found with alias '{model_alias}'")
    creation_timestamp = model_version.creation_timestamp
    version = model_version.version

    # Get the artifact root path
    run = client.get_run(model_version.run_id)
    artifact_root = "/" + "/".join(
        run.info.artifact_uri.split("/")[3:]
    )  # Cause we keep mlruns in /mlruns
    logger.info(f"Artifact root: {artifact_root}")
    logger.info(f"Files in artifact root: {os.listdir(artifact_root)}")

    ckpt_path = None
    for root, dirs, files in os.walk(artifact_root):
        for file in files:
            if file.endswith(".ckpt") and "epoch_" in file:
                ckpt_path = os.path.join(root, file)
                break
        if ckpt_path:
            break
    if not ckpt_path:
        raise ValueError("No checkpoint file found in model artifacts")

    if cfg.suf:
        sys.argv.append(f"--config-name=eval_{cfg.suf}.yaml")
    sys.argv.append(f"+ckpt_path=/{ckpt_path}")  # hack to remove after compose api is available
    metrics = main_eval()

    # Update Prometheus metrics
    accuracy_metric.set(metrics["test/acc"])
    loss_metric.set(metrics["test/loss"])
    creation_timestamp_metric.set(creation_timestamp)
    version_metric.set(version)

    # Push metrics to Prometheus Push Gateway
    push_to_gateway("pushgateway:9091", job="model_evaluation", registry=registry)
