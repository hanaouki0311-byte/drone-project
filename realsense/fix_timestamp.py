import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from rclpy.time import Time

class TimestampFixer(Node):
    def __init__(self):
        super().__init__('timestamp_fixer')

        # RGB画像
        self.rgb_sub = self.create_subscription(
            Image,
            '/camera/camera/color/image_raw',
            self.rgb_callback, 10)
        self.rgb_pub = self.create_publisher(
            Image,
            '/camera/camera/color/image_raw_fixed', 10)

        # 深度画像
        self.depth_sub = self.create_subscription(
            Image,
            '/camera/camera/depth/image_rect_raw',
            self.depth_callback, 10)
        self.depth_pub = self.create_publisher(
            Image,
            '/camera/camera/depth/image_rect_raw_fixed', 10)

        # カメラ情報
        self.info_sub = self.create_subscription(
            CameraInfo,
            '/camera/camera/color/camera_info',
            self.info_callback, 10)
        self.info_pub = self.create_publisher(
            CameraInfo,
            '/camera/camera/color/camera_info_fixed', 10)

    def rgb_callback(self, msg):
        msg.header.stamp = self.get_clock().now().to_msg()
        self.rgb_pub.publish(msg)

    def depth_callback(self, msg):
        msg.header.stamp = self.get_clock().now().to_msg()
        self.depth_pub.publish(msg)

    def info_callback(self, msg):
        msg.header.stamp = self.get_clock().now().to_msg()
        self.info_pub.publish(msg)

def main():
    rclpy.init()
    node = TimestampFixer()
    rclpy.spin(node)

if __name__ == '__main__':
    main()
