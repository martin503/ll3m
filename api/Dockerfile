ARG DOCKER_BASE_IMAGE_SHA
ARG DOCKER_PLATFORM
FROM --platform=${DOCKER_PLATFORM} python:3.9-slim@${DOCKER_BASE_IMAGE_SHA}

RUN mkdir /api
WORKDIR /api

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["sh", "-c", "uvicorn api:app --port 8086 --host 0.0.0.0"]
