# Use the official PostgreSQL image as a base
FROM postgres:latest

# Set environment variables for database and user
ENV POSTGRES_DB=chatdb
ENV POSTGRES_USER=dstaapp
ENV POSTGRES_PASSWORD=dstaapp

ENV TZ=Asia/Singapore
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Bake the schema into the image so tables are created on first startup.
# Postgres automatically runs all *.sql files in this directory when the
# data directory is initialised.
COPY setup.sql /docker-entrypoint-initdb.d/01_setup.sql

# Expose the default PostgreSQL port
EXPOSE 5432