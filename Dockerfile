FROM fedora:29
LABEL \
    name="Operators Manifests Push Service" \
    vendor="Red Hat, Inc" \
    license="GPLv3"

# The caller can optionally provide a cacert url
ARG cacert_url=undefined

ENV WORKERS_NUM 8

WORKDIR /src
RUN dnf -y install \
    python3-gunicorn \
    python3-flask \
    python3-jsonschema \
    python3-koji \
    python3-pyyaml \
    python3-requests \
    python3-operator-courier \
    && dnf -y clean all \
    && rm -rf /tmp/*

RUN if [ "$cacert_url" != "undefined" ]; then \
        cd /etc/pki/ca-trust/source/anchors \
        && curl -O $cacert_url \
        && update-ca-trust extract; \
    fi
# This will allow a non-root user to install a custom root CA at run-time
RUN chmod 777 /etc/pki/tls/certs/ca-bundle.crt
COPY . .
RUN pip3 install . --no-deps
USER 1001
EXPOSE 8080
ENTRYPOINT docker/install-ca.sh && gunicorn-3 --workers ${WORKERS_NUM} --bind 0.0.0.0:8080 --access-logfile=- --enable-stdio-inheritance omps.app:app
