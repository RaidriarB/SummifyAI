import os
import logging
import ffmpeg
import imageio_ffmpeg
from .errors import Codes, format_message

logger = logging.getLogger(__name__)

def preprocess_video(video_path, output_dir=None):
    """
    视频预处理，将视频转换为音频

    Args:
        video_path (str): 视频文件路径
        output_dir (str): 输出目录（可选）

    Returns:
        str: 生成的音频文件路径，如果处理失败则返回 None
    """
    try:
        logger.debug(f'开始视频预处理，输入文件路径: {video_path}')
        # 检查输入文件是否存在
        if not os.path.exists(video_path):
            logger.error(format_message(Codes.INPUT_NOT_FOUND, f'输入文件不存在: {video_path}'))
            return None

        # 构建输出文件路径，使用 m4a 容器
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{base_name}_音频.m4a")
        else:
            base, _ = os.path.splitext(video_path)
            output_path = f"{base}_音频.m4a"

        # 构造 ffmpeg 处理链
        # 使用 stream.audio 来仅保留音频流，并禁用视频（vn）
        # 合并音频滤镜：高通、低通、降噪、音量正规化
        stream = ffmpeg.input(video_path)
        stream = ffmpeg.output(
            stream.audio,
            output_path,
            vn=None,                     # 禁用视频
            acodec='aac',                # 使用 AAC 编码器
            ac=2,                        # 双声道
            ar=44100,                    # 采样率 44.1 kHz
            audio_bitrate='128k',        # 音频比特率 128 kbps
            af='highpass=f=200,lowpass=f=3000,afftdn=nf=-25,loudnorm=I=-16:LRA=11:TP=-1.5',
            y=None                      # 覆盖已存在的文件
        )

        # 获取 ffmpeg 可执行文件的路径，imageio_ffmpeg 会自动下载所需的二进制文件
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        logger.debug(f'使用 ffmpeg 可执行文件: {ffmpeg_exe}')

        # 执行 ffmpeg 处理链
        # 如果处理失败，ffmpeg.run 会抛出 ffmpeg.Error 异常
        ffmpeg.run(stream, cmd=ffmpeg_exe, capture_stdout=True, capture_stderr=True)

        logger.debug(f'视频预处理完成，输出文件路径: {output_path}')
        return output_path

    except Exception as e:
        logger.error(format_message(Codes.PREPROCESS_FAIL, '视频预处理过程出错', str(e)))
        return None
