import subprocess
import os
import logging
import time
import sys

import config

logger = logging.getLogger(__name__)

def transcribe_audio(audio_path, prompt, n_threads=4):
    """
    使用buzz命令进行音频转写
    
    Args:
        audio_path (str): 音频文件路径
        prompt (str): 转写提示词
        n_threads (int): 使用的线程数，默认为4
    
    Returns:
        str or None: 转写成功时返回转写文件名，失败时返回None
    """
    try:
        # 将相对路径转换为绝对路径
        audio_path = os.path.abspath(audio_path)
        if not os.path.exists(audio_path):
            logger.error(f'输入文件不存在: {audio_path}')
            return None
            
        logger.info(f'开始音频转写，输入文件路径: {audio_path}，使用线程数: {n_threads}')
        start_time = time.time()
        
        # 设置环境变量参数
        env = {
            'BUZZ_WHISPERCPP_N_THREADS': str(n_threads),
            **os.environ
        }
        
        # 构建命令参数列表
        cmd = [
            'buzz',
            'add',
            '--task', 'transcribe',
            '--model-type', config.TRANS_MODEL_TYPE,
            '--model-size', config.TRANS_MODEL_SIZE,
            '--prompt', prompt,
            '--txt',
            '--hide-gui',
            audio_path
        ]

        # # 根据平台添加对应路径
        # additional_paths = []
        # if sys.platform.startswith('win'):
        #     # Windows 平台
        #     additional_paths.append(r"C:\Program Files (x86)\Buzz")
        # elif sys.platform == 'darwin':
        #     # macOS 平台
        #     additional_paths.append(r"/Applications/Buzz.app/Contents/MacOS/Buzz")
        # # TODO 如果需要支持 Linux，可以在这里添加对应的路径

        # # 更新当前进程的 PATH 环境变量，将新的路径放在前面
        # os.environ["PATH"] = os.pathsep.join(additional_paths + [os.environ.get("PATH", "")])

        # 执行命令
        subprocess.run(cmd, env=env, check=True)
        
        # 检查转写结果文件
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        dir_path = os.path.dirname(audio_path)
        
        # 获取目录下所有文件
        files = [f for f in os.listdir(dir_path) if f.startswith(base_name) and f.endswith('.txt') and 'on' in f]
        
        if not files:
            logger.error('未找到转写结果文件')
            return None
            
        # 按修改时间排序，获取最新的文件
        files.sort(key=lambda x: os.path.getmtime(os.path.join(dir_path, x)), reverse=True)
        current_file = files[0]
        logger.debug(f'找到最新的转写文件: {current_file}')

        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f'音频转写完成，耗时: {elapsed_time:.2f}秒，输出文件将保存在输入文件所在目录')
        return current_file
    except subprocess.CalledProcessError as e:
        logger.error(f'音频转写过程出错: {e}')
        return None
    except Exception as e:
        logger.error(f'执行音频转写时发生未知错误: {e}')
        return None