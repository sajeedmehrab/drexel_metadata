FROM ghcr.io/imageomics/dataverse-access:0.0.3 as model_fetcher
ARG DATAVERSE_API_TOKEN
ENV DATAVERSE_URL=https://datacommons.tdai.osu.edu/
ENV MODEL_DV_DOI=doi:10.5072/FK2/MMX6FY

# Download model_final.pth
RUN mkdir -p /model \
    && dva download $MODEL_DV_DOI /model

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
COPY Pipfile /pipeline/.

# Install requirements
RUN pipenv install --skip-lock --system && pipenv --clear

COPY config /pipeline/config
COPY --from=model_fetcher /model/cache/torch/hub/checkpoints/model_final.pth \
                          /pipeline/output/enhanced/model_final.pth
COPY gen_metadata.py /pipeline

CMD echo "python gen_metadata.py"
