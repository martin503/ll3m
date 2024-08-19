from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
from datasets import Dataset
from lightning import LightningDataModule
from torch.utils.data import DataLoader
from transformers import (
    DataCollatorForLanguageModeling,
    DataCollatorWithPadding,
    PreTrainedTokenizer,
    PreTrainedTokenizerFast,
)


class LLMDataModule(LightningDataModule):
    """`LightningDataModule` for the data from llm-zoomcamp-2024-competition.

    A `LightningDataModule` implements 7 key methods:

    ```python
        def prepare_data(self):
        # Things to do on 1 GPU/TPU (not on every GPU/TPU in DDP).
        # Download data, pre-process, split, save to disk, etc...

        def setup(self, stage):
        # Things to do on every process in DDP.
        # Load data, set variables, etc...

        def train_dataloader(self):
        # return train dataloader

        def val_dataloader(self):
        # return validation dataloader

        def test_dataloader(self):
        # return test dataloader

        def predict_dataloader(self):
        # return predict dataloader

        def teardown(self, stage):
        # Called on every process in DDP.
        # Clean up after fit or test.
    ```

    This allows you to share a full dataset without explaining how to download,
    split, transform and process the data.

    Read the docs:
        https://lightning.ai/docs/pytorch/latest/data/datamodule.html
    """

    def __init__(
        self,
        train_csv: str,
        predict_csv: str,
        tokenizer: Union[PreTrainedTokenizer, PreTrainedTokenizerFast],
        train_val_test_split: Tuple[int, int, int] = (80, 10, 10),
        batch_size: int = 4,
        num_workers: int = 0,
        pin_memory: bool = False,
        pad_to_multiple_of: int = 8,
        max_length: Optional[int] = None,
    ) -> None:
        """Initialize a `LLMDataModule`.

        :param train_csv: The path to the train csv file.
        :param predict_csv: The path to the predict csv file.
        :param tokenizer: The tokenizer compatible with the model.
        :param train_val_test_split: The train, validation and test split. Defaults to `(80, 10, 10)`.
        :param batch_size: The batch size. Defaults to `4`.
        :param num_workers: The number of workers. Defaults to `0`.
        :param pin_memory: Whether to pin memory. Defaults to `False`.
        :param pad_to_multiple_of: Pad the input and label sequences to multiples of this value.
        :param max_length: The maximum length of the sequence. Defaults to no maximum length.
        """
        if max_length and max_length % pad_to_multiple_of != 0:
            raise (
                ValueError(
                    f"Maximal context length {max_length} is not multiple of pad multiple of {pad_to_multiple_of}"
                )
            )

        super().__init__()

        # this line allows to access init params with 'self.hparams' attribute
        # also ensures init params will be stored in ckpt
        self.save_hyperparameters(logger=False)

        # Tokenizer
        self.hparams.tokenizer.pad_token = self.hparams.tokenizer.eos_token
        self.hparams.tokenizer.padding_side = "right"

        self.data_train: Optional[Dataset] = None
        self.data_val: Optional[Dataset] = None
        self.data_test: Optional[Dataset] = None
        self.data_predict: Optional[Dataset] = None

        self.batch_size_per_device = batch_size

    @property
    def tokenizer(self) -> PreTrainedTokenizer:
        """A shortcut to access the tokenizer since we use the same tokenizer for all the data."""
        return self.hparams.tokenizer

    def preprocess_function(
        self, examples: Dict[str, List[str]], input_format: str = "Question: {}\nAnswer: "
    ) -> Dict[str, List[Union[List[int], List[float]]]]:
        inputs = self.hparams.tokenizer(
            [input_format.format(problem_text) for problem_text in examples["problem_text"]],
            truncation=True,
            max_length=self.hparams.max_length,
        )

        if "answer" in examples:
            inputs["query_len"] = [len(i) for i in inputs["input_ids"]]
            answer = self.hparams.tokenizer(examples["answer"])
            inputs["input_ids"] = [i + a for i, a in zip(inputs["input_ids"], answer["input_ids"])]
            inputs["attention_mask"] = [
                i + a for i, a in zip(inputs["attention_mask"], answer["attention_mask"])
            ]

        return inputs

    def prepare_data(self) -> None:
        """Download data if needed. Lightning ensures that `self.prepare_data()` is called only
        within a single process on CPU, so you can safely add your downloading logic within. In
        case of multi-node training, the execution of this hook depends upon
        `self.prepare_data_per_node()`.

        Do not use it to assign state (self.x = y).
        """
        pass

    def setup(self, stage: Optional[str] = None) -> None:
        """Load data. Set variables: `self.data_train`, `self.data_val`, `self.data_test`.

        This method is called by Lightning before `trainer.fit()`, `trainer.validate()`, `trainer.test()`, and
        `trainer.predict()`, so be careful not to execute things like random split twice! Also, it is called after
        `self.prepare_data()` and there is a barrier in between which ensures that all the processes proceed to
        `self.setup()` once the data is prepared and available for use.

        :param stage: The stage to setup. Either `"fit"`, `"validate"`, `"test"`, or `"predict"`. Defaults to ``None``.
        """
        # Divide batch size by the number of devices.
        if self.trainer is not None:
            if self.hparams.batch_size % self.trainer.world_size != 0:
                raise RuntimeError(
                    f"Batch size ({self.hparams.batch_size}) is not divisible by the number of devices ({self.trainer.world_size})."
                )
            self.batch_size_per_device = self.hparams.batch_size // self.trainer.world_size

        # load and split datasets only if not loaded already
        if not self.data_train and not self.data_val and not self.data_test:
            train_data = pd.read_csv(self.hparams.train_csv).sample(frac=1)
            train, val, test = self.hparams.train_val_test_split

            data_train_val_test = Dataset.from_pandas(train_data).train_test_split(
                val + test, train, shuffle=True
            )
            self.data_train = data_train_val_test["train"]

            data_val_test = data_train_val_test["test"].train_test_split(test, val, shuffle=False)
            self.data_val = data_val_test["train"]
            self.data_test = data_val_test["test"]

            # Apply tokenization to the entire dataset
            self.data_train = self.data_train.map(
                self.preprocess_function, batched=True, remove_columns=["problem_text", "answer"]
            )
            self.data_val = self.data_val.map(
                self.preprocess_function, batched=True, remove_columns=["problem_text", "answer"]
            )
            self.data_test = self.data_test.map(
                self.preprocess_function, batched=True, remove_columns=["problem_text", "answer"]
            )

        # load dataset only if not loaded already
        if not self.data_predict and stage == "predict":
            predict_data = pd.read_csv(self.hparams.predict_csv)
            self.data_predict = Dataset.from_pandas(predict_data)
            self.data_predict = self.data_predict.map(
                self.preprocess_function, batched=True, remove_columns=["problem_text"]
            )

    def train_dataloader(self) -> DataLoader[Any]:
        return DataLoader(
            dataset=self.data_train,
            batch_size=self.batch_size_per_device,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=True,
            collate_fn=DataCollatorForLanguageModeling(
                self.hparams.tokenizer,
                pad_to_multiple_of=self.hparams.pad_to_multiple_of,
                mlm=False,
            ),
        )

    def val_dataloader(self) -> DataLoader[Any]:
        """Create and return the validation dataloader.

        :return: The validation dataloader.
        """
        return DataLoader(
            dataset=self.data_val,
            batch_size=self.batch_size_per_device,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=False,
            collate_fn=DataCollatorForLanguageModeling(
                self.hparams.tokenizer,
                pad_to_multiple_of=self.hparams.pad_to_multiple_of,
                mlm=False,
            ),
        )

    def test_dataloader(self) -> DataLoader[Any]:
        """Create and return the test dataloader.

        :return: The test dataloader.
        """
        return DataLoader(
            dataset=self.data_test,
            batch_size=self.batch_size_per_device,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=False,
            collate_fn=DataCollatorForLanguageModeling(
                self.hparams.tokenizer,
                pad_to_multiple_of=self.hparams.pad_to_multiple_of,
                mlm=False,
            ),
        )

    def predict_dataloader(self) -> DataLoader[Any]:
        """Create and return the prediction dataloader.

        :return: The prediction dataloader.
        """
        return DataLoader(
            dataset=self.data_predict,
            batch_size=self.batch_size_per_device,
            num_workers=self.hparams.num_workers,
            pin_memory=self.hparams.pin_memory,
            shuffle=False,
            collate_fn=DataCollatorWithPadding(
                self.hparams.tokenizer,
                padding=True,
            ),
        )

    def teardown(self, stage: Optional[str] = None) -> None:
        """Lightning hook for cleaning up after `trainer.fit()`, `trainer.validate()`,
        `trainer.test()`, and `trainer.predict()`.

        :param stage: The stage being torn down. Either `"fit"`, `"validate"`, `"test"`, or `"predict"`.
            Defaults to ``None``.
        """
        pass

    def state_dict(self) -> Dict[Any, Any]:
        """Called when saving a checkpoint. Implement to generate and save the datamodule state.

        :return: A dictionary containing the datamodule state that you want to save.
        """
        return {}

    def load_state_dict(self, state_dict: Dict[str, Any]) -> None:
        """Called when loading a checkpoint. Implement to reload datamodule state given datamodule
        `state_dict()`.

        :param state_dict: The datamodule state returned by `self.state_dict()`.
        """
        pass
