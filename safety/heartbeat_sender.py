#!/usr/bin/env python3
"""
hertbeat_sender.py : ノートPCからjetsonにハートビートを送る
INTERVAL秒ごとにUDPでメッセージを送る
止めるときはCtrl＋C
"""

import socket
import time

# =====パラメータ=====
JETSON_IP = '10.35.101.118'
PORT = 14600
INTERVAL = 0.2
#===================

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
seq = 0
print(f'{JETSON_IP}:{PORT}に{INTERVAL}秒ごとに送信します(Ctrl+Cで停止)')

try:
    while True:
        try:
            sock.sendto(f'hb{seq}'.encode(), (JETSON_IP, PORT))
        except OSError as e:
            #wifiが途切れると送信じたいエラーになることがある．止まらずにおくりつづける
            print(f'送信エラー:{e}')
        if seq % 25 == 0:
            print(f'送信中...{seq}')
        seq += 1
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print('\n stoped to send')