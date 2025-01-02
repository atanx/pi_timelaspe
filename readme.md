# 1.使用crontab定时运行
```bash
# 编辑crontab
crontab -e

# 添加以下行（每小时执行一次）
0 * * * * /home/pi/gitee/pi_timelaspe/venv/bin/python3 /home/pi/gitee/pi_timelaspe/timelapse_cv.py
# 每10分钟执行一次
# */10 * * * * /home/pi/gitee/pi_timelaspe/venv/bin/python3 /home/pi/gitee/pi_timelaspe/timelapse_cv.py
crontab -l
```


# 2.使用服务文件方式定时运行 [可选]
```bash
# 创建服务文件
sudo nano /etc/systemd/system/timelapse.service
```

```bash
[Unit]
Description=Timelapse Camera Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/gitee/timelapse/timelapse_cv.py
WorkingDirectory=/home/pi/gitee/timelapse
User=pi
Group=pi
Restart=always
RestartSec=3600

[Install]
WantedBy=multi-user.target
```


## 启动服务
```bash
sudo systemctl enable timelapse
sudo systemctl start timelapse
```

## 查看服务状态
```bash
sudo systemctl status timelapse
```