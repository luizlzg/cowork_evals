# The container that reproduces the CoWork image. See docs/docker.md for the design and
# docs/runtime.md for the inventory every version below is a row of.
#
# The build context is this directory's sibling `data/`, the two requirements files and
# nothing else. No source tree is copied and no credential is installed.

FROM ubuntu:22.04

# The Claude Code CLI version. The one deliberate delta against docs/runtime.md, which
# records corepack and npm as the only npm globals.
ARG CLAUDE_CODE_VERSION
# Set by buildx from --platform. The LibreOffice tarball is named by the kernel
# architecture, so it is mapped below.
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

# One apt layer: the document, image, media and CLI tooling jammy already carries at the
# recorded versions, the Java 11 the tabula-py pin needs, the nine suppliers of
# /usr/lib/python3/dist-packages, the Ubuntu font stack, bubblewrap for the Bash sandbox,
# and the headers the sdist-only pins compile against.
#
# The font list carries the Noto fallback faces and not fonts-noto-core, which alone adds
# 192 families over what docs/runtime.md records.
RUN apt-get update \
  && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    wget \
    jq \
    git \
    openssh-client \
    build-essential \
    pkg-config \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    libcairo2-dev \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    libfreetype6-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    pandoc \
    poppler-utils \
    ghostscript \
    qpdf \
    tesseract-ocr \
    imagemagick \
    ffmpeg \
    default-jre-headless \
    bubblewrap \
    command-not-found \
    pipx \
    python3-apt \
    python3-dbus \
    python3-distro-info \
    python3-gi \
    python3-pyinotify \
    ufw \
    unattended-upgrades \
    fontconfig \
    fonts-crosextra-caladea \
    fonts-crosextra-carlito \
    fonts-dejavu \
    fonts-droid-fallback \
    fonts-font-awesome \
    fonts-liberation \
    fonts-liberation2 \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    fonts-noto-mono \
    fonts-texgyre \
    fonts-urw-base35 \
    lmodern \
    libcups2 \
    libdbus-glib-1-2 \
    libgl1 \
    libice6 \
    libsm6 \
    libxinerama1 \
    libxrandr2 \
    libxrender1 \
  && rm -rf /var/lib/apt/lists/*

# An optional extra root CA, for a host whose network inspects TLS. It arrives as a build
# secret read from SSL_CERT_FILE, never from the build context, and is absent on a network
# that does not intercept. docs/docker.md.
ENV EXTRA_CA_FILE=/usr/local/share/ca-certificates/extra_ca.crt
RUN --mount=type=secret,id=extra_ca \
  set -eux; \
  if [ -s /run/secrets/extra_ca ]; then \
    cp /run/secrets/extra_ca "${EXTRA_CA_FILE}"; \
    update-ca-certificates; \
  fi

# LibreOffice from the upstream deb set. Jammy ships 7.3, and the 26.2 pyuno is what
# unoserver==3.7 needs. The upstream release is named 26.2.5 and soffice reports 26.2.5.2.
# TARGETARCH is Docker's name for the architecture; the archive uses two others, one for
# the directory and one for the file name.
ARG LIBREOFFICE_RELEASE=26.2.5
RUN set -eux; \
  case "${TARGETARCH:-arm64}" in \
    arm64) lo_dir=aarch64; lo_file=aarch64 ;; \
    amd64) lo_dir=x86_64; lo_file=x86-64 ;; \
    *) echo "unsupported TARGETARCH ${TARGETARCH}" >&2; exit 1 ;; \
  esac; \
  tarball="LibreOffice_${LIBREOFFICE_RELEASE}_Linux_${lo_file}_deb.tar.gz"; \
  cd /tmp; \
  curl -fsSLO "https://download.documentfoundation.org/libreoffice/stable/${LIBREOFFICE_RELEASE}/deb/${lo_dir}/${tarball}"; \
  tar -xzf "${tarball}"; \
  dpkg -i LibreOffice_"${LIBREOFFICE_RELEASE}"*_Linux_*_deb/DEBS/*.deb; \
  rm -rf /tmp/"${tarball}" /tmp/LibreOffice_"${LIBREOFFICE_RELEASE}"*_Linux_*_deb; \
  ln -s "$(ls -d /opt/libreoffice*)" /opt/libreoffice; \
  ln -s /opt/libreoffice/program/soffice /usr/local/bin/soffice

# pyuno lives under the deb set's own program directory, so `import uno` resolves from the
# system interpreter. docs/docker.md.
ENV PYTHONPATH=/opt/libreoffice/program

# Node.js from NodeSource. Jammy ships 12.
ARG NODE_VERSION=22.23.2-1nodesource1
RUN set -eux; \
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg; \
  echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list; \
  apt-get update; \
  apt-get install -y "nodejs=${NODE_VERSION}"; \
  rm -rf /var/lib/apt/lists/*

# uv, from the Astral installer. Absent from jammy.
ARG UV_VERSION=0.12.3
RUN set -eux; \
  export UV_UNMANAGED_INSTALL=/usr/local/bin; \
  curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh

# The 127 pins that install off the VM. The other 9 came from apt above, into
# /usr/lib/python3/dist-packages, where pip freeze still sees them. docs/docker.md.
ARG PIP_VERSION=25.3
COPY requirements_installable.txt /tmp/requirements_installable.txt
RUN set -eux; \
  python3 -m pip install --upgrade "pip==${PIP_VERSION}"; \
  python3 -m pip install --no-cache-dir -r /tmp/requirements_installable.txt; \
  rm /tmp/requirements_installable.txt

# The harness. Not part of the CoWork image, and the one added npm global.
RUN npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

# The container runs with the host user's numeric uid and gid, which has no passwd entry.
# HOME is set to the first of these at run time, and the two mounts land under the second.
RUN mkdir -p /tmp/eval-home /work/plugin /work/logs \
  && chmod 0777 /tmp/eval-home /work /work/plugin /work/logs

WORKDIR /work
