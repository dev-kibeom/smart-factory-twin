cmake_minimum_required(VERSION 3.8)
project(smart_factory_sim)

find_package(ament_cmake REQUIRED)

# 맵, URDF, 런치 파일을 인스턴스 설치 영역(share/)으로 공유 마운트 파이프 정합
install(
  DIRECTORY launch map urdf
  DESTINATION share/${PROJECT_NAME}
)

ament_package()