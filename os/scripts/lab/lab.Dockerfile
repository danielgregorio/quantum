# DruidOS ISO lab image - built and run on Forge by scripts/lab/remote.sh.
# One image for both halves of the lab: remastering the ISO
# (scripts/build-iso.sh, needs --privileged for loop mounts/chroot) and
# booting it under QEMU+KVM (scripts/lab/harness.py, needs --device /dev/kvm).
#
# Ubuntu 24.04 on purpose: same base as the ISO being remastered, so the
# squashfs/xorriso tooling matches what produced the original image.
FROM ubuntu:24.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates wget \
        xorriso squashfs-tools genisoimage \
        qemu-system-x86 qemu-utils ovmf \
        python3 python3-pil tesseract-ocr \
        openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
