from pathlib import Path

import pytest
import torch
from transformers import PreTrainedTokenizer

from llm.data.llm_datamodule import LLMDataModule
from llm.data.mnist_datamodule import MNISTDataModule


@pytest.mark.parametrize("batch_size", [32, 128])
def test_mnist_datamodule(batch_size: int) -> None:
    """Tests `MNISTDataModule` to verify that it can be downloaded correctly, that the necessary
    attributes were created (e.g., the dataloader objects), and that dtypes and batch sizes
    correctly match.

    :param batch_size: Batch size of the data to be loaded by the dataloader.
    """
    data_dir = "data/"

    dm = MNISTDataModule(data_dir=data_dir, batch_size=batch_size)
    dm.prepare_data()

    assert not dm.data_train and not dm.data_val and not dm.data_test
    assert Path(data_dir, "MNIST").exists()
    assert Path(data_dir, "MNIST", "raw").exists()

    dm.setup()
    assert dm.data_train and dm.data_val and dm.data_test
    assert dm.train_dataloader() and dm.val_dataloader() and dm.test_dataloader()

    num_datapoints = len(dm.data_train) + len(dm.data_val) + len(dm.data_test)
    assert num_datapoints == 70_000

    batch = next(iter(dm.train_dataloader()))
    x, y = batch
    assert len(x) == batch_size
    assert len(y) == batch_size
    assert x.dtype == torch.float32
    assert y.dtype == torch.int64


@pytest.mark.parametrize("batch_size", [1, 2, 4, 16])
def test_llm_datamodule(batch_size: int, tokenizer: PreTrainedTokenizer) -> None:
    """Tests `LLMDataModule` to verify that it can be created correctly, that the necessary
    attributes were created (e.g., the dataloader objects), and that dtypes and batch sizes
    correctly match.

    :param batch_size: Batch size of the data to be loaded by the dataloader.
    """
    train_csv = "data/train.csv"
    predict_csv = "data/test.csv"

    max_length = 128
    pad_to_multiple_of = 8
    dm = LLMDataModule(
        train_csv,
        predict_csv,
        tokenizer,
        batch_size=batch_size,
        max_length=max_length,
        pad_to_multiple_of=pad_to_multiple_of,
    )

    dm.setup()
    assert dm.data_train and dm.data_val and dm.data_test
    assert dm.train_dataloader() and dm.val_dataloader() and dm.test_dataloader()

    num_datapoints = len(dm.data_train) + len(dm.data_val) + len(dm.data_test)
    assert num_datapoints == 100

    batch = next(iter(dm.train_dataloader()))

    assert len(batch["problem_id"]) == batch_size
    assert len(batch["input_ids"]) == batch_size
    assert len(batch["attention_mask"]) == batch_size
    assert len(batch["query_len"]) == batch_size

    assert batch["input_ids"].shape[1] % pad_to_multiple_of == 0
    assert batch["attention_mask"].shape[1] % pad_to_multiple_of == 0

    dm.setup("predict")
    assert dm.data_predict

    batch = next(iter(dm.predict_dataloader()))
    num_datapoints = len(dm.data_predict)
    assert num_datapoints == 100

    assert len(batch["problem_id"]) == batch_size
    assert len(batch["input_ids"]) == batch_size
    assert len(batch["attention_mask"]) == batch_size
