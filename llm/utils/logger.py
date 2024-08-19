import os
import tempfile
from pathlib import Path

import mlflow
import yaml
from lightning.pytorch.callbacks.model_checkpoint import ModelCheckpoint
from lightning.pytorch.loggers.mlflow import MLFlowLogger
from lightning.pytorch.loggers.utilities import _scan_checkpoints
from torch import Tensor


class CustomMLFlowLogger(MLFlowLogger):
    def _scan_and_log_checkpoints(self, checkpoint_callback: ModelCheckpoint) -> None:
        # get checkpoints to be saved with associated score
        checkpoints = _scan_checkpoints(checkpoint_callback, self._logged_model_time)

        # log iteratively all new checkpoints
        for t, p, s, tag in checkpoints:
            metadata = {
                # Ensure .item() is called to store Tensor contents
                "score": s.item() if isinstance(s, Tensor) else s,
                "original_filename": Path(p).name,
                "Checkpoint": {
                    k: getattr(checkpoint_callback, k)
                    for k in [
                        "monitor",
                        "mode",
                        "save_last",
                        "save_top_k",
                        "save_weights_only",
                        "_every_n_train_steps",
                        "_every_n_val_epochs",
                    ]
                    # ensure it does not break if `Checkpoint` args change
                    if hasattr(checkpoint_callback, k)
                },
            }
            aliases = (
                ["latest", "best"] if p == checkpoint_callback.best_model_path else ["latest"]
            )

            # Artifact path on mlflow
            artifact_path = f"model/checkpoints/{Path(p).stem}"

            # Log the checkpoint
            self.experiment.log_artifact(self._run_id, p, artifact_path)

            # Put model in registry
            # mlflow.pytorch.log_model(

            # Create a temporary directory to log on mlflow
            with tempfile.TemporaryDirectory(
                prefix="test", suffix="test", dir=os.getcwd()
            ) as tmp_dir:
                # Log the metadata
                with open(f"{tmp_dir}/metadata.yaml", "w") as tmp_file_metadata:
                    yaml.dump(metadata, tmp_file_metadata, default_flow_style=False)

                # Log the aliases
                with open(f"{tmp_dir}/aliases.txt", "w") as tmp_file_aliases:
                    tmp_file_aliases.write(str(aliases))

                # Log the metadata and aliases
                self.experiment.log_artifacts(self._run_id, tmp_dir, artifact_path)

            # remember logged models - timestamp needed in case filename didn't change (lastkckpt or custom name)
            self._logged_model_time[p] = t
