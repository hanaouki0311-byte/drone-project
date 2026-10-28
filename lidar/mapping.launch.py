# 手持ちで LiDAR 地図を作る（モーターは回さない）
# 使い方:
#   ros2 launch ~/drone-project/lidar/mapping.launch.py port:=/dev/serial/by-path/xxxx
# port には LiDAR のポートを指定する（ttyUSB0 は Pixhawk のことが多いので注意）

import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

HERE = os.path.dirname(os.path.realpath(__file__))


def generate_launch_description():
    port = LaunchConfiguration('port')

    return LaunchDescription([
        DeclareLaunchArgument('port', description='LiDAR のシリアルポート'),

        # LiDAR（A1M8 は 115200bps）
        Node(
            package='rplidar_ros',
            executable='rplidar_composition',
            output='screen',
            parameters=[{
                'serial_port': port,
                'serial_baudrate': 115200,
                'frame_id': 'laser',
                'angle_compensate': True,
            }],
        ),

        # 機体中心 → LiDAR（取り付け位置。決まったら数値を入れる）
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=['--frame-id', 'base_link', '--child-frame-id', 'laser'],
        ),

        # オドメトリなしの代わり（odom と base_link を常に同じ位置にする）
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=['--frame-id', 'odom', '--child-frame-id', 'base_link'],
        ),

        # slam_toolbox
        IncludeLaunchDescription(
            os.path.join(get_package_share_directory('slam_toolbox'),
                         'launch', 'online_async_launch.py'),
            launch_arguments={
                'slam_params_file': os.path.join(HERE, 'mapper_params.yaml'),
                'use_sim_time': 'false',  # 既定が true（シミュレーション用）なので必ず false
            }.items(),
        ),
    ])
