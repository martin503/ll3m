from pydantic import BaseModel, Field


class Model(BaseModel):
    name: str = Field(description="Model name in the registry.")
    version: str = Field(description="Version of the model to move to prod, must be in staging!")


class Train(BaseModel):
    experiment: str = Field("example", description="Name of the experiment config yaml")
    suf: str = Field("", description="If you do not want to use train.yml")


class Eval(BaseModel):
    path: str = Field(description="Path to torch ckpt from mlruns dir")
    suf: str = Field("", description="If you do not want to use eval.yml")


class Monitor(BaseModel):
    name: str = Field("llm", description="Model name in registry")
    suf: str = Field("", description="Config for eval suffix")
