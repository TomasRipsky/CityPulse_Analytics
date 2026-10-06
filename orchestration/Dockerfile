# The deployed version of CityPulse: Airflow plus the pipeline, built from one commit of the repo.
# Build from the repository root:  make airflow-build ENV=dev
FROM apache/airflow:3.3.2-python3.13

ARG GIT_REVISION=unknown
LABEL org.opencontainers.image.source="https://github.com/TomasRipsky/CityPulse_Analytics" \
      org.opencontainers.image.revision="${GIT_REVISION}"
ENV CITYPULSE_REVISION="${GIT_REVISION}" \
    UV_PYTHON_DOWNLOADS=never \
    UV_COMPILE_BYTECODE=1

# The pipeline gets its own environment, from the lock file, next to (not inside) Airflow's: the
# exact versions the tests ran with, and no dependency fight with Airflow's providers.
USER airflow
RUN pip install --no-cache-dir "uv==0.12.19"
WORKDIR /opt/citypulse
COPY --chown=airflow:root pyproject.toml uv.lock README.md .python-version ./
COPY --chown=airflow:root src ./src
RUN uv sync --locked --no-default-groups --group transform
COPY --chown=airflow:root transform ./transform
RUN cp transform/profiles.yml.example transform/profiles.yml

COPY --chown=airflow:root orchestration/dags /opt/airflow/dags
WORKDIR /opt/airflow
