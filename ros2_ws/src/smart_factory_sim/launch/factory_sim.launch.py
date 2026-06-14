import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node


def generate_launch_description():
    pkg_sim_share = get_package_share_directory("smart_factory_sim")
    pkg_gazebo_ros = get_package_share_directory("gazebo_ros")

    # [스케일 다운 규칙] UI 그래픽 렌더링에 소모되는 VRAM을 완전 소거하기 위한 headless 강제 활성화 [cite: 186, 251]
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gazebo.launch.py")
        ),
        launch_arguments={
            "gui": "false",
            "server": "true",
        }.items(),  # headless:=true 모드 구동 [cite: 186]
    )

    # 로봇 상태 퍼블리셔 등록 (URDF 로드)
    urdf_file = os.path.join(pkg_sim_share, "urdf", "amr.urdf")
    with open(urdf_file, "r") as infp:
        robot_desc = infp.read()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_desc}],
    )

    # 격리형 가상 공장 2D 맵 서버 가동
    map_yaml_file = os.path.join(pkg_sim_share, "map", "factory_map.yaml")
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[{"yaml_filename": map_yaml_file, "use_sim_time": True}],
    )

    # 내장 라이프사이클 매니저로 맵 서버 활성화 제어
    map_manager = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_map",
        output="screen",
        parameters=[
            {"use_sim_time": True},
            {"autostart": True},
            {"node_names": ["map_server"]},
        ],
    )

    return LaunchDescription([gazebo, robot_state_publisher, map_server, map_manager])
