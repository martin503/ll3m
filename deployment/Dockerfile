ARG DOCKER_BASE_IMAGE_SHA
ARG DOCKER_PLATFORM
FROM --platform=${DOCKER_PLATFORM} python:3.9-slim@${DOCKER_BASE_IMAGE_SHA}

RUN mkdir /deployment
WORKDIR /deployment

COPY requirements.txt .
RUN pip install --timeout 1000 -r requirements.txt

COPY . ./deployment
CMD ["sh", "-c", "sleep 15 && python -m deployment.deploy"]
