FROM python:3.11.9-slim-bullseye

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt update && apt upgrade -y
RUN apt-get update && apt-get upgrade -y

# Install Graphviz system package (provides the 'dot' binary needed to render
# behaviour-tree images).  The Python 'graphviz' package in requirements.txt is
# only a thin wrapper and does NOT include the dot executable.
RUN apt-get install -y --no-install-recommends graphviz && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip


# Install pip requirements
ADD build/requirements.txt .
# RUN pip uninstall -y -r requirements.txt --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir

WORKDIR /src