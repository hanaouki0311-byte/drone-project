import numpy as np
from PIL import Image

# 地図サイズ（1ピクセル = 5cm、200x200 = 10m x 10m）
width, height = 200, 200

# 白（255）= 通れる場所
map_data = np.ones((height, width), dtype=np.uint8) * 255

# 外壁（黒 = 0）
map_data[0:5, :] = 0    # 上
map_data[-5:, :] = 0    # 下
map_data[:, 0:5] = 0    # 左
map_data[:, -5:] = 0    # 右

# 障害物（棚や柱のイメージ）
map_data[50:70, 50:70] = 0    # 左上に障害物
map_data[130:150, 130:150] = 0  # 右下に障害物
map_data[80:120, 90:110] = 0   # 真ん中に細長い障害物

# 保存
img = Image.fromarray(map_data, mode='L')
img.save('/tmp/sample_map.pgm')
print("地図を保存しました: /tmp/sample_map.pgm")

# yaml も作成
with open('/tmp/sample_map.yaml', 'w') as f:
    f.write("""image: sample_map.pgm
resolution: 0.05
origin: [-5.0, -5.0, 0.0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196
""")
print("yamlを保存しました: /tmp/sample_map.yaml")
