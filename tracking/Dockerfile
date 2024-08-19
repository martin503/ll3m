ARG DOCKER_BASE_IMAGE_SHA
ARG DOCKER_PLATFORM
FROM --platform=${DOCKER_PLATFORM} python:3.9-slim@${DOCKER_BASE_IMAGE_SHA}

WORKDIR /mlruns

COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["sh", "-c", "mlflow server --backend-store-uri sqlite:////mlruns/mlflow.db --default-artifact-root file:///mlruns --host=0.0.0.0"]
