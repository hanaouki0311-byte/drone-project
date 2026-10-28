# drone-project
 
卒業研究「屋内植物の葉面積を、ドローンの自律飛行で自動計測する」のコード置き場。
メインは葉面積推定。地図作成と飛行は「計測に必要な精度が出れば十分」という方針。
 
## ⚠️ 安全ルール（最優先）
- **モーターが回るコマンドは、実行前に必ずユーザーに確認すること。** ユーザーが機体とプロペラの状態を見てから許可する。
  - 対象：アーム（`/mavros/cmd/arming`）、モード変更で OFFBOARD にするもの、`mavros/hop_test*.py`、Actuator Test 相当の操作
- PX4パラメータの変更も、実行前に内容を説明して確認を取ること。
- 緊急停止（強制ディスアーム、空中でも停止）：
```bash
  ros2 service call /mavros/cmd/command mavros_msgs/srv/CommandLong "{command: 400, param1: 0.0, param2: 21196.0}"
```
 
## ハード構成
| 部品 | 型番など |
|---|---|
| 機体 | Holybro X500 V2（モーター：標準の Holybro 2216 KV920） |
| FC | Pixhawk 6C（PX4） |
| コンパニオン | Jetson Orin Nano（Ubuntu 24.04、ユーザー名 gojura） |
| Jetson↔Pixhawk | TELEM1 ↔ CP2102（USB-UART）→ `/dev/ttyUSB0`、57600bps |
| ESC | DShot600、Pixhawk の **AUX 1〜4** に接続 |
| LiDAR | RPLIDAR A1M8（互換品） |
| 深度カメラ | RealSense D405（T265 も手元にあり） |
| バッテリー | LiPo 4S 8000mAh（5000mAhが無いため）。PM02D 未着のため FC はモバイルバッテリー給電 |
| 送信機 | なし（緊急停止は SSH 越しのコマンドのみ） |
 
## ソフト構成
- ROS2 Jazzy、MAVROS（`/mavros/...`）
- slam_toolbox（2D地図・自己位置推定）、Nav2（自律航行・予定）
- YOLO26-seg（葉の検出）、Open3D（点群処理・葉面積計算）
- RTABMap（D405 で試した。`realsense/start_slam.sh`）
## ディレクトリ
```
drone-project/
  ├── CLAUDE.md
  ├── README.md
  ├── yolo/        YOLO 関連（test_yolo.py など）
  ├── realsense/   start_slam.sh、fix_timestamp.py
  ├── mavros/      Pixhawk 連携（hop_test*.py）
  ├── lidar/       mapping.launch.py（LiDAR + slam_toolbox）、mapper_params.yaml、maps/
  └── lidar_sim/   make_map.py（サンプル2D地図生成）
```
YOLO の仮想環境は `~/yolo_env`。
 
## よく使うコマンド
```bash
# MAVROS 起動（別ターミナルで開いたままにする）
source /opt/ros/jazzy/setup.bash
ros2 launch mavros px4.launch fcu_url:=/dev/ttyUSB0:57600
 
# 状態確認
ros2 topic echo /mavros/state --once
 
# パラメータ確認・変更
ros2 param get /mavros/param <NAME>
ros2 param set /mavros/param <NAME> <VALUE>

# LiDAR 地図作成（手持ち。ポートは差し込み口で固定の by-path 名）
ros2 launch ~/drone-project/lidar/mapping.launch.py port:=/dev/serial/by-path/platform-3610000.usb-usb-0:2.4:1.0-port0
ros2 run tf2_ros tf2_echo map base_link        # 自己位置の確認
ros2 run nav2_map_server map_saver_cli -f ~/drone-project/lidar/maps/room1 --fmt png   # 地図保存
```
 
## 設定済みの PX4 パラメータ
| パラメータ | 値 | 理由 |
|---|---|---|
| `MAV_0_CONFIG` | TELEM 1 | Jetson との MAVLink |
| `MAV_0_FLOW_CTRL` | Force off | 通信が出なかったため |
| `COM_RC_IN_MODE` | 4 | 送信機なしでアーム |
| `PWM_AUX_TIM0` | -4 | AUX を DShot600 に |
| `EKF2_GPS_CTRL` | 0 | GPS なし |
| `EKF2_HGT_REF` | Baro | 高度は気圧計 |
| `COM_ARM_WO_GPS` | 1 | GPS なしでアーム許可 |
 
## 進捗（2026-10-24 時点）
- MAVROS ↔ Pixhawk 通信 OK（`connected: true`）
- ESC を DShot600 に変更し、4モーターが同時に回ることを確認。位置と回転方向も OK
- `mavros/hop_test*.py`：OFFBOARD で姿勢は水平、推力だけを 0→上限→0 と変化させる浮上テスト（紐で固定して実施）
  - 0.22：浮かない（確認用）
  - 0.45：脚が3本浮いた。1本残る
  - 0.50：未確認
- 1つのモーターだけ手ではじくと止まるのが少し早い。浮かない脚との関係は未確認
- 起動時は毎回 Hold（AUTO.LOITER）になる。送信機がないため仕様
- 2026-10-28：LiDAR（A1M8、約6.8Hz）+ slam_toolbox を手持ちで起動し、`map → base_link` が移動に追従することを確認
  - オドメトリなし（`odom → base_link` を静的 TF で 0）。`minimum_travel_distance/heading` を 0 にしないとスキャンが処理されない
  - 地図はまだ保存していない
## 次にやること
1. 手持ちで部屋を一周して地図を保存（`lidar/maps/`）。壁が二重になるなら Pixhawk の yaw → rf2o の順でオドメトリを追加
2. 0.50 で4本とも浮くか確認。残る脚が毎回同じかを見る
3. LiDAR + slam_toolbox の位置を PX4 の EKF に送る（`/mavros/vision_pose/pose` など）
   - `EKF2_EV_CTRL` の有効化、`EKF2_EV_DELAY` の調整が必須（参考：Linguerri 2025 の修士論文）
   - slam_toolbox の解像度は 0.05m 程度にして Jetson の負荷を抑える
4. 位置制御でホバリング → 目的地へ自律飛行（Nav2 か、位置 setpoint を順に送る簡単なスクリプト）
5. D405 + YOLO で葉を検出し、葉面積を計算
## 注意点
- 起動直後に MAVROS に出る `FCU: EVENT ... with args` は、PX4 のアーム前チェック情報。MAVROS では読めないので、詳細は QGC で確認する
- OFFBOARD に入るには、切り替え前から setpoint を 2Hz 以上で流し続ける必要がある
- ユーザーは ROS や Linux に慣れてきている途中。コマンドは1つずつ、意味を添えて示すとよい
- Pixhawk も LiDAR も CP2102 なので、`ttyUSB0/1` は入れ替わり得る。`/dev/serial/by-path/` で指定する（2.3 の口 = Pixhawk、2.4 の口 = LiDAR）
- SSH 接続では画面がないので `gnome-terminal` は使えない。複数ノードは launch ファイルにまとめる
- slam_toolbox の `online_async_launch.py` は `use_sim_time` の既定が true。実機では必ず false にする
