import functools

import hydra
from loguru import logger
from omegaconf import DictConfig
from prefect import task

from llm.eval import evaluate as hydra_eval
from llm.train import train as hydra_train
from llm.utils import extras


def hydra_main(*args, **kw):
    """
    Hack to make returns work per:
    https://github.com/facebookresearch/hydra/issues/332#issuecomment-1824568934
    """

    main = hydra.main(*args, **kw)

    def main_decorator(f):
        returned_values = []

        @functools.wraps(f)
        def f_wrapper(*args, **kw):
            ret = f(*args, **kw)
            returned_values.append(ret)
            return ret

        wrapped = main(f_wrapper)

        @functools.wraps(wrapped)
        def main_wrapper(*args, **kw):
            wrapped(*args, **kw)
            return returned_values[0] if len(returned_values) == 1 else returned_values

        return main_wrapper

    return main_decorator


@hydra.main(version_base="1.3", config_path="../configs", config_name="train.yaml")
def main_train(cfg: DictConfig) -> None:
    extras(cfg)
    hydra_train(cfg)


@hydra_main(version_base="1.3", config_path="../configs", config_name="eval.yaml")
def main_eval(cfg: DictConfig) -> dict:
    extras(cfg)
    metric_dict, object_dict = hydra_eval(cfg)
    return metric_dict


@task
def update_model_tag(client, model_name, version, old_tag, new_tag):
    try:
        model_version = client.get_model_version(name=model_name, version=version)
        if model_version.tags.get("stage") == old_tag:
            client.set_model_version_tag(
                name=model_name, version=version, key="stage", value=new_tag
            )
            logger.info(f"Updated {model_name} version {version} from {old_tag} to {new_tag}")
        return model_version
    except Exception as e:
        logger.error(f"Error updating {model_name} version {version}: {str(e)}")
