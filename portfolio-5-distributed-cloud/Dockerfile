# Optional lab image. Not built in the supplied execution environment.
FROM python:3.13-slim
WORKDIR /app
COPY node.py node_schema.sql client.py replicator.py /app/
RUN mkdir -p /state && chown -R 10001:10001 /state /app
USER 10001:10001
ENV PYTHONUNBUFFERED=1
CMD ["python", "node.py", "--help"]
