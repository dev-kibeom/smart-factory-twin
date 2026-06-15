FROM osrf/ros:humble-desktop-full AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# NVIDIA 그래픽 가속 활성화
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute,video

# 1. 필수 시스템 종속성 및 Gazebo / Nav2 컴포넌트 라이브러리 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-setuptools \
    python3-colcon-common-extensions \
    python3-gi \
    python3-gi-cairo \
    python3-psutil \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-gazebo-ros \
    ros-humble-nav2-bringup \
    ros-humble-nav2-map-server \
    ros-humble-nav2-lifecycle-manager \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-behaviortree-cpp \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0 \
    gir1.2-gst-plugins-bad-1.0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-nice \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    && rm -rf /var/lib/apt/lists/*

# 2. [FRS-12.1] CPU 백래시(Falling back to cpu)를 완벽히 차단하는 정식 CUDA 가속 휠 세트 이식
# jax와 jaxlib 외에, JAX가 NVIDIA 드라이버 커널에 다이렉트로 결합할 수 있도록 관련 쿠다 플러그인 컴포넌트들을 함께 명시합니다.
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
    mujoco \
    mujoco-mjx \
    numpy && \
    pip3 install --no-cache-dir \
    jax[cuda12] \
    -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html \
    paho-mqtt \
    websocket-client

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

WORKDIR /workspace/ros2_ws
# COPY ros2_ws/src ./src

# 4. 엔트리포인트 오버레이 소스 자동 등록 체계 안착
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "if [ -f /workspace/ros2_ws/install/setup.bash ]; then source /workspace/ros2_ws/install/setup.bash; fi" >> ~/.bashrc

CMD ["/bin/bash"]