# smart_factory_twin/ros2_ws/src/ros2_medkit/CMakeLists.txt
cmake_minimum_required(VERSION 3.8)
project(ros2_medkit)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -std=c++17)
endif()

# ---------------------------------------------------------------------------
# [의존성 패키지] ROS 2 표준 메시지 및 커스텀 인터페이스 인입
# ---------------------------------------------------------------------------
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)       # 🔌 [인프라 수복] 표준 센서 메시지 패키지 탐색
find_package(factory_interfaces REQUIRED) # 🔌 [인프라 수복] 고장 주입 서비스 인터페이스 탐색

include_directories(include)

# ---------------------------------------------------------------------------
# [Executable 1] 핵심 진단 및 결함 변조 프록시 노드 빌드
# ---------------------------------------------------------------------------
add_executable(diagnostics_node src/diagnostics_node.cpp)
ament_target_dependencies(diagnostics_node
  rclcpp
  sensor_msgs
  factory_interfaces
)

# ---------------------------------------------------------------------------
# [Executable 2] 진단 링크 스텁 엔진 노드 빌드
# ---------------------------------------------------------------------------
add_executable(bt_engine_node src/bt_engine_node.cpp)
ament_target_dependencies(bt_engine_node
  rclcpp
  std_msgs
)

# ---------------------------------------------------------------------------
# [배포 레이어] 설치 경로 박제
# ---------------------------------------------------------------------------
install(TARGETS
  diagnostics_node
  bt_engine_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()