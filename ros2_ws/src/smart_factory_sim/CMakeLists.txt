cmake_minimum_required(VERSION 3.8)
project(smart_factory_sim)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ---------------------------------------------------------------------------
# [의존성 인입 패키지] ROS2 인프라 코어 컴포넌트 링커
# ---------------------------------------------------------------------------
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclpy REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(factory_interfaces REQUIRED)
find_package(behaviortree_cpp REQUIRED)

include_directories(
  include
  /usr/include
)

# ---------------------------------------------------------------------------
# [C++ 컴파일 엔진 1] Task 2-5: BehaviorTree.CPP v4 임무 조율 노드 빌드
# ---------------------------------------------------------------------------
add_executable(bt_mission_coordinator src/bt_mission_coordinator.cpp)
ament_target_dependencies(bt_mission_coordinator
  rclcpp
  std_msgs
  geometry_msgs
  factory_interfaces
  behaviortree_cpp
)

# ---------------------------------------------------------------------------
# [C++ 컴파일 엔진 2] Task 2-4: OpenPLC 제어용 OPC UA 필드버스 브릿지 노드 빌드
# ---------------------------------------------------------------------------
add_executable(ros2_opc_ua_bridge_node src/ros2_opc_ua_bridge_node.cpp)

# 🔌 [핫픽스 완정 수복] open62541 파편화를 지우고 ROS2 전용 패키지만 안전 수전
ament_target_dependencies(ros2_opc_ua_bridge_node
  rclcpp
  std_msgs
  factory_interfaces
)

# 🔌 [링커 분리 인터록] 순수 일반 C++ 공유 라이브러리는 독자적인 링커 명세로 밀결착
target_link_libraries(ros2_opc_ua_bridge_node
  open62541
)

# ---------------------------------------------------------------------------
# [배포 레이어] Executables 설치 경로 박제
# ---------------------------------------------------------------------------
install(TARGETS
  bt_mission_coordinator
  ros2_opc_ua_bridge_node
  DESTINATION lib/${PROJECT_NAME}
)

install(PROGRAMS
  smart_factory_sim/jax_physics_engine.py
  smart_factory_sim/integrated_control_node.py
  smart_factory_sim/webrtc_streamer_node.py
  smart_factory_sim/sysid_optimization_engine.py
  smart_factory_sim/core_affinity_manager.py
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY
  launch
  map
  urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()