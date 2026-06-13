FROM osrf/ros:humble-desktop-full AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute,video

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash-completion \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    ros-humble-nav2-bringup \
    ros-humble-rmw-cyclonedds-cpp \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    && rm -rf /var/lib/apt/lists/*

ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# ---------------------------------------------------------------------------
# 빌드 컨텍스트 루트(.) 구조에 맞게 복사 경로 패싱 정합
# ---------------------------------------------------------------------------
WORKDIR /workspace/ros2_ws

# 컨텍스트 루트(.) 기준으로 명확하게 'ros2_ws/src' 전체를 컨테이너 내부 './src' 폴더로 복사합니다.
COPY ros2_ws/src ./src

RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --symlink-install"

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source /workspace/ros2_ws/install/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && source install/setup.bash && exec bash"]