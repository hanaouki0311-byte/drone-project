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
| バッテリー | LiPo 4S 5000mAh（2026-10-29 に 8000mAh から交換） |
| パワーモジュール | PM02（アナログ式、D なし）→ Pixhawk の POWER1。FC はこれで給電（モバイルバッテリー不要に） |
| 電源系統 | **Jetson も同じ LiPo から給電**。LiPo を抜くと Jetson・Pixhawk・ESC が全部落ちる |
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
# by-path 名はコロンを含み MAVROS の URL として読めないので、readlink で ttyUSBx に変換して渡す
ros2 launch mavros px4.launch fcu_url:=$(readlink -f /dev/serial/by-path/platform-3610000.usb-usb-0:2.4:1.0-port0):57600
 
# 状態確認
ros2 topic echo /mavros/state --once
 
# パラメータ確認・変更
ros2 param get /mavros/param <NAME>
ros2 param set /mavros/param <NAME> <VALUE>

# LiDAR 地図作成（手持ち。ポートは差し込み口で固定の by-path 名）
ros2 launch ~/drone-project/lidar/mapping.launch.py port:=/dev/serial/by-path/platform-3610000.usb-usb-0:2.2:1.0-port0
ros2 run tf2_ros tf2_echo map base_link        # 自己位置の確認
ros2 run nav2_map_server map_saver_cli -f ~/drone-project/lidar/maps/room1 --fmt png   # 地図保存
```
 
## 設定済みの PX4 パラメータ
| パラメータ | 値 | 理由 |
|---|---|---|
| `MAV_0_CONFIG` | TELEM 1 | Jetson との MAVLink |
| `MAV_0_FLOW_CTRL` | Force off | 通信が出なかったため |
| `COM_RC_IN_MODE` | 4 | 送信機なしでアーム |
| `PWM_AUX_TIM0` | -3 | AUX を DShot（2026-10-29 に実機で -3 を確認。-3 = DShot600 のはずだが要確認。以前の記述 -4 は誤り）|
| `EKF2_GPS_CTRL` | 0 | GPS なし |
| `EKF2_HGT_REF` | Baro | 高度は気圧計 |
| `COM_ARM_WO_GPS` | 1 | GPS なしでアーム許可 |
| `BAT1_SOURCE` / `BAT1_N_CELLS` | 0 / 4 | PM02（アナログ）から読む、4S |
| `BAT1_V_DIV` / `BAT1_A_PER_V` | 18.1 / 36.37 | PM02 V3 の係数（公表値 18.182 / 36.364）。テスターで電圧を合わせ込む予定 |
| `BAT1_CAPACITY` | 5000 | 4S 5000mAh（2026-10-29 に 8000 から変更） |
 
## 進捗（2026-10-24 時点）
- MAVROS ↔ Pixhawk 通信 OK（`connected: true`）
- ESC を DShot600 に変更し、4モーターが同時に回ることを確認。位置と回転方向も OK
- `mavros/hop_test*.py`：OFFBOARD で姿勢は水平、推力だけを 0→上限→0 と変化させる浮上テスト（紐で固定して実施）
  - 0.22：浮かない（確認用）
  - 0.45：脚が3本浮いた。1本残る
  - 0.50：2026-10-30 に2回実施（どちらも約8秒で停止）。ログは logs/hop_20261029_192845
- 手ではじくと止まるのが早いのは2番モーター（左後ろ）。2026-10-30 のテスト記録でも、浮く瞬間に毎回左後ろが下がる（0.50 で最大 約4°）→ 2番モーターの摩擦（ベアリング・異物）を疑う。浮いた後は PX4 が 1° 以内に補正
- 起動時は毎回 Hold（AUTO.LOITER）になる。送信機がないため仕様
- 2026-10-28：LiDAR（A1M8、約6.8Hz）+ slam_toolbox を手持ちで起動し、`map → base_link` が移動に追従することを確認
  - オドメトリなし（`odom → base_link` を静的 TF で 0）。`minimum_travel_distance/heading` を 0 にしないとスキャンが処理されない
  - 地図はまだ保存していない
- 2026-10-29：PM02 から Pixhawk への 5V が不安定
  - LiPo + PM02 だけでは Pixhawk の LED が点かないことがあった。USB-C 給電なら起動・通信 OK（本体は無事）
  - USB-C を抜くとしばらく PM02 で動くが、途中で IMU が止まり ESC がピーピー鳴り出した（Pixhawk の信号が途切れた）
  - PM02 の電圧センサーは正常（15.6V を読めた）。疑い：PM02 の 5V 出力／6ピンケーブル／POWER1 の口
  - 2026-10-30 朝：PM02 だけで起動し、約 10 分間 IMU 5Hz・接続とも途切れず安定。前回は 6 ピンケーブルの接触不良の可能性が高い（ケーブルを固定する）
  - **解決するまでモーターを回すテストはしない**
- 2026-10-30：0.50 のテスト後に「High Accelerometer Bias」（EVENT 3613628、Y軸 0.40 > 上限 約0.39）でアーム拒否。再起動で一度解消したが、テストを重ねた後に再びアーム拒否（理由は未確認）。加速度キャリブレーションを検討
## 次にやること
1. 手持ちで部屋を一周して地図を保存（`lidar/maps/`）。壁が二重になるなら Pixhawk の yaw → rf2o の順でオドメトリを追加
2. 0.50 で4本とも浮くか確認。残る脚が毎回同じかを見る
3. LiDAR + slam_toolbox の位置を PX4 の EKF に送る（`/mavros/vision_pose/pose` など）
   - `EKF2_EV_CTRL` の有効化、`EKF2_EV_DELAY` の調整が必須（参考：Linguerri 2025 の修士論文）
   - slam_toolbox の解像度は 0.05m 程度にして Jetson の負荷を抑える
4. 位置制御でホバリング → 目的地へ自律飛行（Nav2 か、位置 setpoint を順に送る簡単なスクリプト）
5. D405 + YOLO で葉を検出し、葉面積を計算
## 注意点
- 起動直後に MAVROS に出る `FCU: EVENT ... with args` は、PX4 のアーム前チェック情報。MAVROS では読めないが、PX4 の all_events.json.xz（px4-travis.s3.amazonaws.com/Firmware/master/_general/）で番号→文章に変換できる。いつも出るもの：79408 ホーム未設定、453929 送信機なし、6801787 QGC なし、13835193/10011251 位置推定なし、377561 ミッションなし。問題なのは 133277 アーム拒否 など
- OFFBOARD に入るには、切り替え前から setpoint を 2Hz 以上で流し続ける必要がある
- ユーザーは ROS や Linux に慣れてきている途中。コマンドは1つずつ、意味を添えて示すとよい
- Pixhawk も LiDAR も CP2102 なので、`ttyUSB0/1` は入れ替わり得る。`/dev/serial/by-path/` で指定する（2026-10-29 から：2.4 の口 = Pixhawk、2.2 の口 = LiDAR。挿し替えたら受信だけで MAVLink が来る方が Pixhawk）
- SSH 接続では画面がないので `gnome-terminal` は使えない。複数ノードは launch ファイルにまとめる
- slam_toolbox の `online_async_launch.py` は `use_sim_time` の既定が true。実機では必ず false にする
- Pixhawk の I/O の B/E（オレンジ）が約 4Hz で点滅（2026-10-29〜）。I/O 側の MAIN 出力は未使用（モーターは FMU 側の AUX）なので、いったん保留。アーム時に I/O 関連の警告が出ないか注意
- ESC が数秒おきに「ピッ」と鳴るのは、BLHeli_S のビーコン（スロットル 0 が約 10 分続くと鳴る。機体を音で探すための機能）。故障ではない
- ESC の電源は配電ボードに XT30 で挿してあるだけ。地図作りなどモーターを使わない作業では抜いておく（ビーコン停止・節電・誤アームでも回らない）。モーターテストの前に挿し忘れない
