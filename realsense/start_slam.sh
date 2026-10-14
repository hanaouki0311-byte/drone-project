#!/bin/bash

# タブ1: D405カメラ
gnome-terminal --tab -- bash -c "ros2 launch realsense2_camera rs_launch.py enable_sync:=true initial_reset:=true; exec bash"

sleep 3

# タブ2: タイムスタンプ修正
gnome-terminal --tab -- bash -c "source ~/yolo_env/bin/activate && python3 ~/drone-project/realsense/fix_timestamp.py; exec bash"

sleep 1

# タブ3: TF設定
gnome-terminal --tab -- bash -c "ros2 run tf2_ros static_transform_publisher --x 0 --y 0 --z 0 --yaw 0 --pitch 0 --roll 0 --frame-id base_link --child-frame-id camera_link; exec bash"

sleep 1

# タブ4: RTABMap
gnome-terminal --tab -- bash -c "ros2 launch rtabmap_launch rtabmap.launch.py rgb_topic:=/camera/camera/color/image_raw_fixed depth_topic:=/camera/camera/depth/image_rect_raw_fixed camera_info_topic:=/camera/camera/color/camera_info_fixed approx_sync:=true visual_odometry:=true; exec bash"