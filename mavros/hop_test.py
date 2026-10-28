#!/usr/bin/env python3
"""
hop_test.py : 紐で固定した状態で、数秒だけ浮かせて自動で降ろすテスト用スクリプト
- OFFBOARDモードで「姿勢は水平・機首は今の向き」を保ち、推力だけを
  0 → MAX_THRUST までゆっくり上げ、HOLD秒保持し、ゆっくり0まで下げる
- Ctrl+C を押すと、推力0を送ったうえで強制ディスアーム（モーター即停止）
- 位置情報は使わないので、浮くと横に流れます。必ず紐で固定してください。
"""
import math
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from rclpy.signals import SignalHandlerOptions
from mavros_msgs.msg import AttitudeTarget, State
from mavros_msgs.srv import CommandBool, SetMode, CommandLong
from sensor_msgs.msg import Imu

# ===== ここを調整 =====
MAX_THRUST = 0.45   # 最大推力（0〜1）。浮かなければ 0.05 ずつ上げて再実行
RAMP_UP = 6.0       # 0 → MAX_THRUST まで上げる時間 [秒]
HOLD = 3.0          # MAX_THRUST を保つ時間 [秒]
RAMP_DOWN = 4.0     # MAX_THRUST → 0 まで下げる時間 [秒]
RATE = 50.0         # 指令の送信周波数 [Hz]
# ======================


class Hop(Node):
    def __init__(self):
        super().__init__('hop_test')
        self.state = State()
        self.yaw = None

        self.create_subscription(State, '/mavros/state', self.state_cb, 10)
        imu_qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                             history=HistoryPolicy.KEEP_LAST, depth=10)
        self.create_subscription(Imu, '/mavros/imu/data', self.imu_cb, imu_qos)

        self.pub = self.create_publisher(AttitudeTarget, '/mavros/setpoint_raw/attitude', 10)
        self.arm_cli = self.create_client(CommandBool, '/mavros/cmd/arming')
        self.mode_cli = self.create_client(SetMode, '/mavros/set_mode')
        self.cmd_cli = self.create_client(CommandLong, '/mavros/cmd/command')

    def state_cb(self, msg):
        self.state = msg

    def imu_cb(self, msg):
        # 起動時の機首方向（ヨー角）を1回だけ記録し、その向きを保つ
        if self.yaw is None:
            q = msg.orientation
            self.yaw = math.atan2(2.0 * (q.w * q.z + q.x * q.y),
                                  1.0 - 2.0 * (q.y * q.y + q.z * q.z))
            self.get_logger().info(f'機首方向を記録: {math.degrees(self.yaw):.1f} deg')

    def send(self, thrust):
        msg = AttitudeTarget()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.type_mask = 7  # 角速度は無視し、姿勢（orientation）と推力だけを使う
        y = self.yaw if self.yaw is not None else 0.0
        msg.orientation.w = math.cos(y / 2.0)  # ロール0・ピッチ0（水平）
        msg.orientation.z = math.sin(y / 2.0)
        msg.thrust = float(max(0.0, min(thrust, MAX_THRUST)))
        self.pub.publish(msg)

    def force_disarm(self):
        req = CommandLong.Request()
        req.command = 400       # MAV_CMD_COMPONENT_ARM_DISARM
        req.param1 = 0.0        # ディスアーム
        req.param2 = 21196.0    # 強制（空中でも止める）
        return self.cmd_cli.call_async(req)


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    n = Hop()
    dt = 1.0 / RATE
    phase = 'pre'
    t0 = time.time()
    print('MAVROSとの接続と姿勢データを待っています…')

    try:
        while rclpy.ok():
            rclpy.spin_once(n, timeout_sec=0.0)
            now = time.time()
            el = now - t0
            thrust = 0.0

            if phase == 'pre':
                # 推力0の指令を2秒以上流してから OFFBOARD に切り替える（PX4の仕様）
                if not n.state.connected or n.yaw is None:
                    t0 = now
                elif el > 2.0:
                    n.mode_cli.call_async(SetMode.Request(custom_mode='OFFBOARD'))
                    print('OFFBOARD に切り替えます')
                    phase, t0 = 'mode', now

            elif phase == 'mode':
                if n.state.mode == 'OFFBOARD':
                    n.arm_cli.call_async(CommandBool.Request(value=True))
                    print('アームします')
                    phase, t0 = 'arming', now
                elif el > 5.0:
                    print('OFFBOARD に切り替わりませんでした。MAVROSのログを確認してください')
                    break

            elif phase == 'arming':
                if n.state.armed:
                    print(f'上昇開始（最大推力 {MAX_THRUST}）  ※止めるときは Ctrl+C')
                    phase, t0 = 'up', now
                elif el > 5.0:
                    print('アームできませんでした。MAVROSのログを確認してください')
                    break

            elif phase == 'up':
                thrust = MAX_THRUST * el / RAMP_UP
                if el >= RAMP_UP:
                    print('保持')
                    phase, t0 = 'hold', now

            elif phase == 'hold':
                thrust = MAX_THRUST
                if el >= HOLD:
                    print('下降')
                    phase, t0 = 'down', now

            elif phase == 'down':
                thrust = MAX_THRUST * (1.0 - el / RAMP_DOWN)
                if el >= RAMP_DOWN:
                    n.arm_cli.call_async(CommandBool.Request(value=False))
                    print('ディスアームします')
                    phase, t0 = 'done', now

            elif phase == 'done':
                if el > 2.0 or not n.state.armed:
                    print('終了')
                    break

            # 飛行中に OFFBOARD が外れたら（フェイルセーフなど）スクリプトは手を引く
            if phase in ('up', 'hold', 'down') and n.state.mode != 'OFFBOARD':
                print(f'OFFBOARD が解除されました（現在: {n.state.mode}）。終了します')
                break

            n.send(thrust)
            time.sleep(dt)

    except KeyboardInterrupt:
        print('\n中断：推力0を送って強制停止します')
        for _ in range(10):
            n.send(0.0)
            time.sleep(0.02)
        f = n.force_disarm()
        rclpy.spin_until_future_complete(n, f, timeout_sec=2.0)
        print('強制ディスアームを送信しました')

    n.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
