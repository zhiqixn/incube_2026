FROM python:3.11.9-slim-bullseye

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE 1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

RUN apt update && apt upgrade -y
RUN apt-get update && apt-get upgrade -y

# Install Graphviz (provides the 'dot' binary needed by render_bt.py to
# render behaviour-tree images) and libpq-dev/gcc for psycopg2.
RUN apt-get install -y --no-install-recommends graphviz libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip


# Install pip requirements
ADD requirements.txt .
# RUN pip uninstall -y -r requirements.txt --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir

# Use the pre-compiled binary wheel — avoids needing libc6-dev headers
# that were cleaned by the earlier rm -rf /var/lib/apt/lists/*.
RUN pip install psycopg2-binary
