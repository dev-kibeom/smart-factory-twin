# 로봇 실행 레이어용 ROS2 Humble 데스크톱 베이스 이미지 채택
FROM osrf/ros:humble-desktop-full AS base

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# NVIDIA 그래픽 가속 및 가상 디스플레이(X11) 구동 설정 (기범 님의 RTX GPU 자원 참조)
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute,video

# 필수 시스템 종속성 및 GStreamer / ROS2 의존성 라이브러리 설치
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

# [중요] 이전 답변의 피드백 반영: 컨텍스트가 ros2_ws 내부이므로 상대 경로를 아래와 같이 정합합니다.
WORKDIR /workspace/ros2_ws
COPY ./src ./src

# 의존성 해결 및 colcon 빌드 자동화 실행
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && colcon build --symlink-install"

RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source /workspace/ros2_ws/install/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && source install/setup.bash && exec bash"]