# Tessera image (edge ingest, sync, hub and live map). Pin the base image by digest before any release build.
FROM python:3.12-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install ".[server]"

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=build /install /usr/local
COPY scripts /opt/tessera/scripts
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin tessera \
    && mkdir /data /keys /trusted \
    && chown 10001:10001 /data /keys /trusted \
    && chmod 700 /keys
USER 10001
WORKDIR /data
ENTRYPOINT ["tessera"]
CMD ["--help"]
