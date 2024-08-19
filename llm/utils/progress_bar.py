import os
import uuid

from lightning.pytorch.callbacks import ProgressBar
from loguru import logger


class LoguruProgressBar(ProgressBar):
    def __init__(self, log_every_n_steps=None, log_every_n_epochs=None):
        super().__init__()
        self._enabled = True
        self.log_every_n_steps = log_every_n_steps
        self.log_every_n_epochs = log_every_n_epochs
        self.training_id = str(uuid.uuid4())[:8]  # Generate a unique ID for this training run
        self.process_id = os.getpid()
        self.current_step = 0
        self.val_batches = 0

    @staticmethod
    def _status(trainer) -> str:
        return f"[ {trainer.current_epoch + 1:0>{len(str(abs(trainer.max_epochs)))}} / {trainer.max_epochs} ]"

    def _log(self, message, trainer=None):
        if self._enabled:
            if trainer:
                message = f"{self._status(trainer)} {message}"
            logger.info(f"[Train: {self.training_id}] [PID: {self.process_id}] {message}")

    def disable(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    def on_train_start(self, *_):
        self._log(f"Training started.")

    def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
        self.current_step += 1
        if isinstance(outputs, dict) and "loss" in outputs:
            loss = outputs["loss"].item()
        else:
            loss = float("nan")

        if self.log_every_n_epochs and (
            (trainer.current_epoch + 1) % self.log_every_n_epochs == 0
            or trainer.current_epoch == trainer.max_epochs - 1
        ):
            self.train_loss += loss
        if self.log_every_n_steps and self.current_step % self.log_every_n_steps == 0:
            self._log(f"Step {self.current_step}, Loss: {loss:.4f}", trainer)

    def on_train_epoch_start(self, trainer, pl_module):
        self.train_loss = 0.0

    def on_train_epoch_end(self, trainer, pl_module):
        current_epoch = trainer.current_epoch
        if self.log_every_n_epochs and (
            (current_epoch + 1) % self.log_every_n_epochs == 0
            or current_epoch == trainer.max_epochs - 1
        ):
            self._log(f"Loss: {self.train_loss/trainer.num_training_batches:.4f}", trainer)

    def on_train_end(self, *_):
        self._log("Training completed")

    def on_validation_start(self, trainer, pl_module):
        self._log("Validation started")
        self.val_loss = 0.0

    def on_validation_batch_end(
        self,
        trainer,
        pl_module,
        outputs,
        batch,
        batch_idx,
        dataloader_idx=0,
    ):
        if isinstance(outputs, dict) and "loss" in outputs:
            loss = outputs["loss"].item()
        else:
            loss = float("nan")
        self.val_loss += loss

        if batch_idx == trainer.num_val_batches[dataloader_idx]:
            self.val_loss /= self.val_batches
            self._log(f"Validation completed, Loss: {self.val_loss:.4f}", trainer)
