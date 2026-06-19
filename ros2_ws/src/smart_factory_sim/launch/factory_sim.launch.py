`# smart_factory_twin/ros2_ws/src/smart_factory_sim/launch/factory_sim.launch.py
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    pkg_sim_share = get_package_share_directory("smart_factory_sim")
    pkg_gazebo_ros = get_package_share_directory("gazebo_ros")

    headless_arg = DeclareLaunchArgument(
        "headless", default_value="True", description="Gazebo GUI 활성화 토글 플래그"
    )

    headless_env = LaunchConfiguration("headless")

    # Gazebo 인프라 연격
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_gazebo_ros, "launch", "gazebo.launch.py")
        ),
        launch_arguments={
            "gui": PythonExpression(
                [
                    "'true' if ",
                    headless_env,
                    " in ['false', 'False', False] else 'false'",
                ]
            ),
            "server": "true",
        }.items(),
    )

    # 로봇 상태 퍼블리셔 등록
    urdf_file = os.path.join(pkg_sim_share, "urdf", "amr.urdf")
    with open(urdf_file, "r") as infp:
        robot_desc = infp.read()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_desc, "use_sim_time": True}],
    )

    # 가상 AMR 강체 스폰 노드
    spawn_amr_entity = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_amr_model",
        output="screen",
        arguments=[
            "-entity",
            "amr_01",
            "-topic",
            "robot_description",
            "-x",
            "0.0",
            "-y",
            "0.0",
            "-z",
            "0.1",
        ],
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

    # 라이프사이클 매니저
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

    # 🔌 [Task 2-5 핵심 결합]: BehaviorTree.CPP v4 임무 조율기 노드를 런치 파이프라인에 전격 등재
    bt_coordinator = Node(
        package="smart_factory_sim",
        executable="bt_mission_coordinator",
        name="bt_mission_coordinator_node",
        output="screen",
        parameters=[{"use_sim_time": True}],
    )

    return LaunchDescription(
        [
            headless_arg,
            gazebo,
            robot_state_publisher,
            spawn_amr_entity,
            map_server,
            map_manager,
            bt_coordinator,  # [행동 트리 제어권 통합 완정]
        ]
    )
