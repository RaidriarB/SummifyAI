import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def preprocess_video(video_path):
    """
    视频预处理，将视频转换为音频
    
    Args:
        video_path (str): 视频文件路径
    
    Returns:
        str: 生成的音频文件路径，如果处理失败则返回None
    """
    try:
        logger.debug(f'开始视频预处理，输入文件路径: {video_path}')
        # 检查输入文件是否存在
        if not os.path.exists(video_path):
            logger.error(f'输入文件不存在: {video_path}')
            return None
            
        # 构建输出文件路径
        output_path = f"{os.path.splitext(video_path)[-2]}_audio.m4a"
        
        # 使用ffmpeg提取音频
        cmd = [
            'ffmpeg',
            '-i', video_path,  # 输入文件
            '-vn',  # 禁用视频
            '-acodec', 'aac',  # 使用AAC编码器
            '-ac', '2',  # 双声道
            '-ar', '44100',  # 采样率44.1kHz
            '-b:a', '128k',  # 音频比特率128kbps
            '-af', 'highpass=f=200,lowpass=f=3000,afftdn=nf=-25',  # 高通滤波器、低通滤波器和降噪
            '-af', 'loudnorm=I=-16:LRA=11:TP=-1.5',  # 音量正规化
            '-y',  # 覆盖已存在的文件
            output_path
        ]
        
        # 执行ffmpeg命令
        process = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 检查命令执行结果
        if process.returncode == 0:
            logger.debug(f'视频预处理完成，输出文件路径: {output_path}')
            return output_path
        else:
            logger.error(f'ffmpeg处理失败: {process.stderr}')
            return None
            
    except Exception as e:
        logger.error(f'视频预处理过程出错: {e}')
        return None