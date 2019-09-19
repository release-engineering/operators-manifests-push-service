FROM fedora:29
LABEL \
    name="Operators Manifests Push Service" \
    vendor="Red Hat, Inc" \
    image="integration" \
    license="GPLv3"

# Test and build dependencies.
RUN dnf -y install \
    git \
    gcc \
    redhat-rpm-config \
    popt-devel \
    rpm-devel \
    krb5-devel \
    python3-devel \
    python3-gunicorn \
    python3-flask \
    python3-jsonschema \
    python3-koji \
    python3-pyyaml \
    python3-requests \
    python3-operator-courier \
    && dnf -y clean all \
    && rm -rf /tmp/*

RUN dnf --enablerepo=updates-testing -y update python3-operator-courier \
    && dnf -y clean all \
    && rm -rf /tmp/*

RUN pip3 install tox coveralls

WORKDIR /src
COPY . .
RUN pip3 install -e .
