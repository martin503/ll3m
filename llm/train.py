from typing import Any, Dict, List, Optional, Tuple

import hydra
import lightning as L
import mlflow
import transformers
from lightning import Callback, LightningDataModule, LightningModule, Trainer
from lightning.pytorch.loggers import Logger
from omegaconf import DictConfig

from llm.utils import (
    RankedLogger,
    extras,
    get_metric_value,
    instantiate_callbacks,
    instantiate_loggers,
    log_hyperparameters,
    task_wrapper,
)

log = RankedLogger(__name__, rank_zero_only=True)


@task_wrapper
def train(cfg: DictConfig) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Trains the model. Can additionally evaluate on a testset, using best weights obtained during
    training.

    This method is wrapped in optional @task_wrapper decorator, that controls the behavior during
    failure. Useful for multiruns, saving info about the crash, etc.

    :param cfg: A DictConfig configuration composed by Hydra.
    :return: A tuple with metrics and dict with all instantiated objects.
    """
    # set seed for random number generators in pytorch, numpy and python.random
    if cfg.get("seed"):
        L.seed_everything(cfg.seed, workers=True)

    log.info(f"Instantiating datamodule <{cfg.data._target_}>")
    datamodule: LightningDataModule = hydra.utils.instantiate(cfg.data)

    log.info(f"Instantiating model <{cfg.model._target_}>")
    model: LightningModule = hydra.utils.instantiate(cfg.model)

    log.info("Instantiating callbacks...")
    callbacks: List[Callback] = instantiate_callbacks(cfg.get("callbacks"))

    log.info("Instantiating loggers...")
    logger: List[Logger] = instantiate_loggers(cfg.get("logger"))

    log.info(f"Instantiating trainer <{cfg.trainer._target_}>")
    trainer: Trainer = hydra.utils.instantiate(cfg.trainer, callbacks=callbacks, logger=logger)

    object_dict = {
        "cfg": cfg,
        "datamodule": datamodule,
        "model": model,
        "callbacks": callbacks,
        "logger": logger,
        "trainer": trainer,
    }

    if logger:
        log.info("Logging hyperparameters!")
        log_hyperparameters(object_dict)

    if cfg.get("train"):
        log.info("Starting training!")
        trainer.fit(model=model, datamodule=datamodule, ckpt_path=cfg.get("ckpt_path"))

    train_metrics = trainer.callback_metrics

    if cfg.get("test"):
        log.info("Starting testing!")
        ckpt_path = trainer.checkpoint_callback.best_model_path
        if ckpt_path == "":
            log.warning("Best ckpt not found! Using current weights for testing...")
            ckpt_path = None
        trainer.test(model=model, datamodule=datamodule, ckpt_path=ckpt_path)
        log.info(f"Best ckpt path: {ckpt_path}")

    test_metrics = trainer.callback_metrics

    if cfg.get("train"):
        # Log the model with MLflow cause MLFlowLogger can store model only as artifact
        mlflow_logger = next(
            (
                logger
                for logger in trainer.loggers
                if isinstance(logger, L.pytorch.loggers.MLFlowLogger)
            ),
            None,
        )
        if mlflow_logger:
            for artifact in mlflow_logger.experiment.list_artifacts(mlflow_logger.run_id):
                with mlflow.start_run(run_id=mlflow_logger.run_id):
                    generator = transformers.pipeline(
                        task="text-generation", model=model.net, tokenizer=datamodule.tokenizer
                    )
                    model_info = mlflow.transformers.log_model(
                        generator, artifact.path, registered_model_name=cfg.model_name
                    )

                    if cfg.get("test"):
                        test_acc = test_metrics["test/acc"]
                        client = mlflow_logger.experiment
                        prod_models = client.search_model_versions(
                            f"name = '{cfg.model_name}' and tag.stage = 'prod'"
                        )

                        is_challenger = True
                        for prod_model in prod_models:
                            run = mlflow.get_run(prod_model.run_id)
                            is_challenger &= (
                                run.data.metrics.get("test/acc") < test_metrics["test/acc"].item()
                            )

                        if len(prod_models) == 0 or is_challenger:
                            mlflow.register_model(
                                model_info.model_uri, cfg.model_name, tags={"stage": "staging"}
                            )
                    else:
                        log.warning("Test accuracy not found. Model registered without staging.")
        else:
            log.warning("MLflow logger not found. Model not logged to MLflow.")

    # merge train and test metrics
    metric_dict = {**train_metrics, **test_metrics}

    return metric_dict, object_dict


@hydra.main(version_base="1.3", config_path="../configs", config_name="train.yaml")
def main(cfg: DictConfig) -> Optional[float]:
    """Main entry point for training.

    :param cfg: DictConfig configuration composed by Hydra.
    :return: Optional[float] with optimized metric value.
    """
    # apply extra utilities
    # (e.g. ask for tags if none are provided in cfg, print cfg tree, etc.)
    extras(cfg)

    # train the model
    metric_dict, _ = train(cfg)

    # safely retrieve metric value for hydra-based hyperparameter optimization
    metric_value = get_metric_value(
        metric_dict=metric_dict, metric_name=cfg.get("optimized_metric")
    )

    # return optimized metric
    return metric_value


if __name__ == "__main__":
    main()
