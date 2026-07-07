FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    git python3 python3-pip python3-dev \
    build-essential ccache g++ gawk \
    wget curl locales tzdata rsync sudo \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /bin/bash builder && \
    echo "builder ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/builder

USER builder
ENV USER=builder
WORKDIR /home/builder/ardupilot

RUN git config --global http.postBuffer 1048576000 && \
    git config --global http.lowSpeedLimit 0 && \
    git config --global http.lowSpeedTime 999999

RUN bash -c ' \
    for attempt in 1 2 3 4 5; do \
        rm -rf /home/builder/ardupilot/* /home/builder/ardupilot/.[!.]* 2>/dev/null; \
        git clone --depth 1 --branch Copter-4.5 --recurse-submodules --shallow-submodules \
            https://github.com/ArduPilot/ardupilot.git . && exit 0; \
        echo "clone attempt ${attempt} failed, retrying"; \
        sleep 10; \
    done; \
    exit 1'

RUN Tools/environment_install/install-prereqs-ubuntu.sh -y

ENV PATH="/home/builder/.local/bin:/home/builder/ardupilot/Tools/autotest:${PATH}"

RUN ./waf configure --board sitl
RUN ./waf copter

EXPOSE 14550/udp

CMD ["python3", "Tools/autotest/sim_vehicle.py", "-v", "ArduCopter", "--out=udp:companion-api:14550", "--no-rebuild"]
