FROM python:3.11

ARG VCS_REF
ARG BUILD_DATE
LABEL \
    maintainer="https://slub-dresden.de" \
    org.label-schema.vendor="Saxon State and University Library Dresden" \
    org.label-schema.name="OCR-D Monitor" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.vcs-url="https://github.com/slub/ocrd_monitor" \
    org.label-schema.build-date=$BUILD_DATE \
    org.opencontainers.image.vendor="Saxon State and University Library Dresden" \
    org.opencontainers.image.title="OCR-D Monitor" \
    org.opencontainers.image.description="Web frontend for OCR-D Manager" \
    org.opencontainers.image.source="https://github.com/slub/ocrd_monitor" \
    org.opencontainers.image.documentation="https://github.com/slub/ocrd_monitor/blob/${VCS_REF}/README.md" \
    org.opencontainers.image.revision=$VCS_REF \
    org.opencontainers.image.created=$BUILD_DATE

RUN apt-get update \
    && apt-get install -o Acquire::Retries=3 -y --no-install-recommends \
    libcairo2-dev libgtk-3-bin libgtk-3-dev libglib2.0-dev \
    libgtksourceview-3.0-dev libgirepository1.0-dev gir1.2-webkit2-4.0 \
    python3-dev pkg-config cmake dnsutils \
    && pip3 install -U setuptools wheel \
    && pip3 install browse-ocrd

# MONITOR_PORT_LOG
EXPOSE 8080
# MONITOR_PORT_WEB
EXPOSE 5000

VOLUME /data

COPY init.sh /init.sh
COPY ocrdbrowser /usr/local/ocrd-monitor/ocrdbrowser
COPY ocrdmonitor /usr/local/ocrd-monitor/ocrdmonitor
COPY pyproject.toml /usr/local/ocrd-monitor/
COPY noxfile.py /usr/local/ocrd-monitor/
COPY tests /usr/local/ocrd-monitor/tests

RUN pip3 install pdm
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /usr/local/ocrd-monitor
RUN pdm install

WORKDIR /
CMD ["/init.sh", "/data"]
