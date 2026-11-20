# Tessera edge image. Pin the base image by digest before any release build.
FROM python:3.15-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.15-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=build /install /usr/local
COPY scripts /opt/tessera/scripts
RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin tessera \
    && mkdir /data \
    && chown 10001:10001 /data
USER 10001
WORKDIR /data
ENTRYPOINT ["tessera"]
CMD ["--help"]
