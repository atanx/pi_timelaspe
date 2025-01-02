import os
import time
from datetime import datetime
import oss2
import cv2
import requests
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

class TimelapseCamera:
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        # OSS配置从环境变量读取
        self.access_key_id = os.getenv('accessKeyID')
        self.access_key_secret = os.getenv('accessKeySecret')
        self.bucket_name = os.getenv('bucketName')
        self.endpoint = os.getenv('endpoint')
        
        # 验证必要的环境变量
        self._validate_env_vars()
        
        # 本地存储配置
        self.base_dir = os.getenv('TIMELAPSE_BASE_DIR', '/home/pi/timelapse')
        self.temp_dir = os.path.join(self.base_dir, 'images')
        self.mock_file = os.getenv('MOCK_FILE', '222.png')
        
        # 相机配置
        self.camera_id = int(os.getenv('CAMERA_ID', '0'))
        self.camera_width = int(os.getenv('CAMERA_WIDTH', '1920'))
        self.camera_height = int(os.getenv('CAMERA_HEIGHT', '1080'))
        self.retry_count = int(os.getenv('CAPTURE_RETRY_COUNT', '3'))
        
        # 文件保留天数
        self.retention_days = int(os.getenv('FILE_RETENTION_DAYS', '7'))
        
        # 飞书配置
        self.feishu_webhook_url = os.getenv('FEISHU_WEBHOOK_URL')
        
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        
        # 初始化相机
        self.setup_camera()
        
        # 初始化OSS客户端
        self.setup_oss()
        
    def _validate_env_vars(self):
        """验证必要的环境变量"""
        required_vars = [
            'accessKeyID',
            'accessKeySecret',
            # 'OSS_BUCKET_NAME',
            'endpoint'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
    
    def setup_logging(self):
        """配置日志"""
        log_file = os.path.join(self.base_dir, 'timelapse.log')
        self.logger = logging.getLogger('timelapse')
        self.logger.setLevel(logging.INFO)
        
        handler = RotatingFileHandler(
            log_file, 
            maxBytes=1024*1024,
            backupCount=5
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        self.logger.addHandler(console)
        
    def setup_camera(self):
        """初始化USB摄像头"""
        try:
            self.camera = cv2.VideoCapture(self.camera_id)
            
            # 设置分辨率
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            
            # 检查摄像头是否成功打开
            if not self.camera.isOpened():
                raise Exception("无法打开摄像头")
                
            # 预热摄像头
            for _ in range(5):
                self.camera.read()
                time.sleep(0.1)
                
            self.logger.info("摄像头初始化成功")
        except Exception as e:
            self.logger.error(f"摄像头初始化失败: {str(e)}")
            raise
            
    def setup_oss(self):
        """初始化OSS客户端"""
        try:
            auth = oss2.Auth(self.access_key_id, self.access_key_secret)
            self.bucket = oss2.Bucket(auth, self.endpoint, self.bucket_name)
            self.logger.info("OSS客户端初始化成功")
        except Exception as e:
            self.logger.error(f"OSS客户端初始化失败: {str(e)}")
            raise
            
    def capture_image(self, mock=False):
        """拍摄照片"""
        if mock:
            return os.path.join(self.temp_dir, self.mock_file), self.mock_file
        
        try:
            # 尝试多次拍照，确保获取到清晰图像
            for _ in range(self.retry_count):
                ret, frame = self.camera.read()
                if ret and frame is not None:
                    break
                time.sleep(0.5)
                
            if not ret or frame is None:
                raise Exception("无法获取图像")
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'timelapse_{timestamp}.jpg'
            filepath = os.path.join(self.temp_dir, filename)
            
            # 保存图片，逆时针旋转90度
            rotated = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            cv2.imwrite(filepath, rotated)
            self.logger.info(f"照片拍摄成功: {filename}")
            
            return filepath, filename
        except Exception as e:
            self.logger.error(f"拍照失败: {str(e)}")
            raise
    
    def save_to_ugreen(self, local_file, remote_file):
        """保存到Ugreen"""
        self.logger.info(f"TODO: 保存到Ugreen: {local_file} -> {remote_file}")
    
    def upload_to_oss(self, local_file, remote_file):
        """上传文件到OSS"""
        try:
            date_prefix = datetime.now().strftime('%Y/%m/%d')
            oss_path = f'raspberry/{date_prefix}/{remote_file}'
            oss_url = f'https://{self.bucket_name}.{self.endpoint}/{oss_path}'
            with open(local_file, 'rb') as f:
                self.bucket.put_object(oss_path, f)
            
            self.logger.info(f"文件上传成功: {oss_path}")
            
            return oss_url
        except Exception as e:
            self.logger.error(f"文件上传失败: {str(e)}")
            raise
    
    def send_feishu_msg(self, oss_path):
        """发送飞书消息"""
        url = self.feishu_webhook_url
        headers = {
            'Content-Type': 'application/json'
        }
        data = {
            'msg_type': 'text',
            'content': {'text': f'文件上传成功: {oss_path}'}
        }
        requests.post(url, headers=headers, json=data)
    
    # def cleanup_old_files(self):
    #     """清理旧文件"""
    #     try:
    #         current_time = time.time()
    #         for file in os.listdir(self.temp_dir):
    #             file_path = os.path.join(self.temp_dir, file)
    #             if os.path.isfile(file_path):
    #                 if current_time - os.path.getmtime(file_path) > self.retention_days * 86400:
    #                     os.remove(file_path)
    #                     self.logger.info(f"删除旧文件: {file}")
    #     except Exception as e:
    #         self.logger.error(f"清理文件失败: {str(e)}")
            
    def run(self):
        """执行一次拍照和上传"""
        try:
            # 拍照
            local_file, filename = self.capture_image(mock=False)
            # 保存到Ugreen
            ugreen_file = f'{filename}.png'
            self.save_to_ugreen(local_file, ugreen_file)
            # 上传
            oss_url = self.upload_to_oss(local_file, filename)
            # 发送飞书消息
            self.send_feishu_msg(oss_url)
            # 清理旧文件
            # self.cleanup_old_files()
            return True
        except Exception as e:
            self.logger.error(f"执行失败: {str(e)}")
            self.send_feishu_msg(f"执行失败: {str(e)}")
            return False
        
    def close(self):
        """关闭摄像头"""
        if hasattr(self, 'camera'):
            self.camera.release()
            self.logger.info("摄像头已关闭")

def main():
    camera = TimelapseCamera()
    try:
        camera.run()
    finally:
        camera.close()

if __name__ == "__main__":
    main()