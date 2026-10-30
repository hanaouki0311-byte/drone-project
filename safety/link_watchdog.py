#!/usr/bin/env python3
"""
link_watchdog.py : ノートPC からのハートビートが途切れたら AUTO.LAND にする
- アーム中にハートビートが TIMEOUT 秒以上届かなければ、着陸モードに切り替える
- 一度もハートビートを受け取っていないままアームした場合も「途切れている」とみなす
- ハートビートが戻っても OFFBOARD には戻さない（再開するかは人が判断する）
"""
import socket
import time

import rclpy
from rclpy.node import Node
from mavros_msgs.msg import State
from mavros_msgs.srv import SetMode

# ===== ここを調整 =====
PORT = 14600        # ノートPC 側と同じ番号にする
TIMEOUT = 2.0       # この秒数届かなければ着陸 [秒]
CHECK = 0.1         # 見張りの間隔 [秒]
RETRY = 1.0         # 着陸指令を送り直す間隔（PX4 が断ったとき用） [秒]
# ======================


class LinkWatchdog(Node):
    def __init__(self):
        super().__init__('link_watchdog')
        self.state = State()
        self.create_subscription(State, '/mavros/state', self.state_cb, 10)
        self.mode_cli = self.create_client(SetMode, '/mavros/set_mode')

        # UDP の受信口。待たずにすぐ戻る（ノンブロッキング）設定にする
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('0.0.0.0', PORT))
        self.sock.setblocking(False)

        self.last_hb = time.monotonic()   # 起動時点を「最後に受け取った時刻」にしておく
        self.got_any = False
        self.lost = False
        self.last_land_req = 0.0

        self.create_timer(CHECK, self.check)
        self.get_logger().info(f'UDP {PORT} でハートビートを待っています（{TIMEOUT} 秒途切れたら着陸）')

    def state_cb(self, msg):
        self.state = msg

    def read_heartbeats(self):
        # 届いているぶんを全部読む。何もなければ BlockingIOError ですぐ抜ける
        while True:
            try:
                data, addr = self.sock.recvfrom(64)
            except BlockingIOError:
                break
            self.last_hb = time.monotonic()
            if not self.got_any:
                self.get_logger().info(f'ハートビート受信開始: {addr[0]}')
                self.got_any = True

    def check(self):
        self.read_heartbeats()
        now = time.monotonic()
        silent = now - self.last_hb

        # 途切れた／戻ったの表示（アームしていなくても知らせる）
        if silent > TIMEOUT and not self.lost:
            self.lost = True
            self.get_logger().warn(f'ハートビートが {silent:.1f} 秒途切れています')
        elif silent <= TIMEOUT and self.lost:
            self.lost = False
            self.get_logger().info('ハートビートが戻りました（モードは自動では戻しません）')

        # 着陸させるのは「アーム中」「途切れている」「まだ AUTO.LAND でない」ときだけ
        if not (self.state.armed and self.lost and self.state.mode != 'AUTO.LAND'):
            return
        if now - self.last_land_req < RETRY:
            return
        self.last_land_req = now
        self.get_logger().error(f'通信断 {silent:.1f} 秒 → AUTO.LAND を要求します（現在: {self.state.mode}）')
        self.mode_cli.call_async(SetMode.Request(custom_mode='AUTO.LAND'))


def main():
    rclpy.init()
    node = LinkWatchdog()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.sock.close()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
