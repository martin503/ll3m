ARG DOCKER_BASE_IMAGE_SHA
ARG DOCKER_PLATFORM
FROM --platform=${DOCKER_PLATFORM} python:3.9-slim@${DOCKER_BASE_IMAGE_SHA}

RUN mkdir /app
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["streamlit", "run", "app.py"]
