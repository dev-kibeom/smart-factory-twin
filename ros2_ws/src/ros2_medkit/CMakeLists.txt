cmake_minimum_required(VERSION 3.8)
project(ros2_medkit)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(factory_interfaces REQUIRED)

# 비헤이비어 트리 실행 엔진 노드 바이너리 타겟 등록 및 링크 체결
add_executable(bt_engine_node src/bt_engine_node.cpp)
ament_target_dependencies(bt_engine_node rclcpp std_msgs factory_interfaces)

# 빌드 완료 후 실행 바이너리 배치 위치 지정
install(TARGETS
  bt_engine_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
