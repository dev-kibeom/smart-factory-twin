# 로봇 실행 레이어용 ROS2 Humble 데스크톱 베이스 이미지 채택
FROM osrf/ros:humble-desktop-full AS base

# 비인터랙티브 모드 설정 및 필수 환경 변수 인가
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

# 1. NVIDIA 그래픽 가속 및 가상 디스플레이(X11) 구동을 위한 필수 환경 변수 주입
# 기범 님의 RTX 4060 GPU 자원을 컨테이너가 Zero-copy 참조하기 위한 설정
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=graphics,utility,compute,video

# 2. 필수 시스템 종속성 및 GStreamer / NVENC 개발 라이브러리 설치
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

# 3. FastDDS/CycloneDDS 공유 메모리 및 네트워크 격리 환경 정합
ENV RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# 4. 워크스페이스 디렉토리 생성 및 소스 코드 복사
WORKDIR /workspace/ros2_ws
COPY ./ros2_ws/src ./src

# 5. 의존성 해결 및 colcon 빌드 자동화 실행 환경 구축
RUN . /opt/ros/humble/setup.sh && \
    colcon build --symlink-install

# 6. 컨테이너 진입 시 ROS2 환경 변수 및 워크스페이스 자동 Source 등록
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && \
    echo "source /workspace/ros2_ws/install/setup.bash" >> ~/.bashrc

ENTRYPOINT ["/bin/bash", "-c", "source /opt/ros/humble/setup.bash && source install/setup.bash && exec bash"]