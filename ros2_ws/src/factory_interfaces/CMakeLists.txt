cmake_minimum_required(VERSION 3.8)
project(factory_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic -Werror)
endif()

# ROS2 코어 빌드 및 인터페이스 생성 필수 디펜던시 패키지 탐색
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# 생성할 커스텀 인터페이스 파일 목록 타겟 바인딩
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/RobotDynamics.msg"
  "msg/SafetyStatus.msg"
  "srv/InjectFault.srv"
  "action/ExecuteTask.action"
  DEPENDENCIES std_msgs builtin_interfaces
)

ament_package()