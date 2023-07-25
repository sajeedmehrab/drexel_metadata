FROM alpine/git:2.40.1 as model_fetcher
ENV MODEL_REPO_URL=https://huggingface.co/imageomics/Drexel-metadata-generator

# Download model_final.pth
RUN mkdir -p /model \
    && cd /model \
    && git clone --depth=1 ${MODEL_REPO_URL}
RUN ls /model

FROM python:3.8.10-slim-buster
LABEL "org.opencontainers.image.authors"="John Bradley <john.bradley@duke.edu>"
LABEL "org.opencontainers.image.description"="Tool to extract metadata information from fish images"

# Install build requirements
RUN apt-get update \
    && apt-get install -y python3-dev git gcc g++ libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install pipenv
RUN pip install --upgrade pip
RUN pip install pipenv

WORKDIR /pipeline

# ADD scripts in /pipeline to the PATH
ENV PATH="/pipeline:${PATH}"

COPY Pipfile /pipeline/.

# Fix issue installing pycallgraph related to use_2to3 being removed from setuptools
RUN pip install setuptools==57.0.0

# Install requirements
RUN pipenv install --skip-lock --system && pipenv --clear

COPY config /pipeline/config
COPY --from=model_fetcher /model/Drexel-metadata-generator/model_final.pth \
                          /pipeline/output/enhanced/model_final.pth

COPY gen_metadata.py /pipeline

# Default to use enhanced model added above (unset DM_CONFIG_FILENAME to use config.json)
ENV DM_CONFIG_FILENAME config_enhance_no_joel.json

CMD echo "python gen_metadata.py"
