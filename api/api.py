import mlflow
from fastapi import FastAPI, HTTPException
from mlflow import MlflowClient
from prometheus_client import Summary
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field

app = FastAPI()
instrumentator = (
    Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)
)


@app.on_event("startup")
async def _startup():
    instrumentator.expose(app)


class ChatInput(BaseModel):
    question: str = Field(
        description="Your question to the model.", example="What is the capital of France?"
    )
    input_format: str = Field(
        description="The structure of text given to model.", default="Question: {}\nAnswer: "
    )
    model_name: str = Field(description="The name of the model to use.", default="llm")


def fetch_model(model_name: str = "llm", model_alias: str = "champ"):
    try:
        client = MlflowClient()
        model_version = client.get_model_version_by_alias(name=model_name, alias=model_alias)
        generator = mlflow.pyfunc.load_model(
            model_uri=f"models:/{model_name}/{model_version.version}"
        )
        return generator
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Model {model_name} with alias {model_alias} not found: {str(e)}",
        )


@app.post("/chat")
def chat_with_model(chat_input: ChatInput):
    try:
        generator = fetch_model(chat_input.model_name)
        input = chat_input.input_format.format(chat_input.question)
        full_response = generator.predict(input)

        # Remove the input format from the beginning of the response
        response = full_response[0].replace(input, "", 1).strip()

        return {"answer": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
