```bash
# 编辑crontab
crontab -e

# 添加以下行（每小时执行一次）
0 * * * * /usr/bin/python3 /home/pi/timelapse/timelapse.py
```


# 创建服务文件
```bash
# 创建服务文件
sudo nano /etc/systemd/system/timelapse.service
```

```bash
[Unit]
Description=Timelapse Camera Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/timelapse/timelapse.py
WorkingDirectory=/home/pi/timelapse
User=pi
Group=pi
Restart=always
RestartSec=3600

[Install]
WantedBy=multi-user.target
```


# 启动服务
```bash
sudo systemctl enable timelapse
sudo systemctl start timelapse
```

# 查看服务状态
```bash
sudo systemctl status timelapse
```