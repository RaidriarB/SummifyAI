import subprocess
import os
import logging
from openai import OpenAI
import anthropic
from concurrent.futures import ThreadPoolExecutor, as_completed


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


def call_ai_api(text, api_key, prompt, api_type='deepseek'):
    """
    调用AI API进行文本处理，支持DeepSeek和Claude
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        prompt (str): 提示词
        api_type (str): API类型，支持'deepseek'和'claude'
    
    Returns:
        str: API返回的处理结果
    """
    try:
        logger.debug(f'开始调用DeepSeek API，输入文本长度: {len(text)}')
        # 创建OpenAI客户端，设置base_url为DeepSeek API地址
        if api_type == 'deepseek':
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=8000,
                temperature=0.9,
                stream=False
            )
        elif api_type == 'claude':
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-2.1",
                max_tokens=8000,
                temperature=0.9,
                system=prompt,
                messages=[
                    {"role": "user", "content": text}
                ]
            )
        
        # 返回生成的内容
        return response.choices[0].message.content
    except Exception as e:
        print(f"调用API时出错: {e}")
        return None

def add_punctuation(text, api_key, prompt, chunk_size=2000, api_type='deepseek'):
    """
    对文本进行分块并调用DeepSeek API添加标点
    
    Args:
        text (str): 原始文本
        api_key (str): DeepSeek API密钥
        prompt (str): 提示词
        chunk_size (int): 分块大小
    
    Returns:
        str: 带有标点的完整文本
    """
    logger.debug(f'开始添加标点，输入文本长度: {len(text)}，分块大小: {chunk_size}')
    # 将文本分块，确保不打断句子
    import re
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # 确保temp目录存在
    temp_dir = 'tempdata/split'
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    # 使用简单的空格分割方法
    sentences = text.split(' ')
    chunks = []
    current_chunk = ''
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= chunk_size:  # +1 for the space
            current_chunk += ('' if not current_chunk else ' ') + sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)
    
    # 保存原始分块
    for idx, chunk in enumerate(chunks):
        chunk_file = os.path.join(temp_dir, f'chunk_{idx}_original.txt')
        save_text_to_file(chunk, chunk_file)
        logger.debug(f'保存原始分块 {idx} 到文件: {chunk_file}')
    
    # 使用线程池并行处理每个分块，使用字典保存顺序
    results_dict = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        # 为每个分块创建带索引的future
        future_dict = {idx: executor.submit(call_ai_api, chunk, api_key, prompt, api_type)
                      for idx, chunk in enumerate(chunks)}
        
        # 等待所有future完成并按索引保存结果
        for idx, future in future_dict.items():
            processed_text = future.result()
            if processed_text:
                results_dict[idx] = processed_text
                # 保存处理后的分块
                processed_file = os.path.join(temp_dir, f'chunk_{idx}_processed.txt')
                save_text_to_file(processed_text, processed_file)
                logger.debug(f'保存处理后分块 {idx} 到文件: {processed_file}')
    
    # 按照原始顺序拼接结果
    ordered_results = [results_dict[i] for i in range(len(chunks)) if i in results_dict]
    return "".join(ordered_results)


def save_text_to_file(text, output_path):
    """
    将处理好的文本保存到指定文件
    
    Args:
        text (str): 要保存的文本内容
        output_path (str): 输出文件路径
    
    Returns:
        bool: 保存是否成功
    """
    try:
        logger.debug(f'开始保存文本到文件，输出路径: {output_path}')
        # 确保目标目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        logger.debug(f'文本保存完成，文件路径: {output_path}')
        return True
    except Exception as e:
        logger.error(f'保存文本到文件时出错: {e}')
        return None

def copy_file(src_path, dst_path):
    """
    复制文件到指定路径
    
    Args:
        src_path (str): 源文件路径
        dst_path (str): 目标文件路径
    
    Returns:
        bool: 复制是否成功
    """
    try:
        logger.debug(f'开始复制文件，源文件: {src_path}, 目标路径: {dst_path}')
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        import shutil
        shutil.copy2(src_path, dst_path)
        logger.debug(f'文件复制完成，目标路径: {dst_path}')
        return True
    except Exception as e:
        logger.error(f'复制文件时出错: {e}')
        return None

def move_file(src_path, dst_path):
    """
    移动文件到指定路径
    
    Args:
        src_path (str): 源文件路径
        dst_path (str): 目标文件路径
    
    Returns:
        bool: 移动是否成功
    """
    try:
        logger.debug(f'开始移动文件，源文件: {src_path}, 目标路径: {dst_path}')
        # 确保目标目录存在
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        import shutil
        shutil.move(src_path, dst_path)
        logger.debug(f'文件移动完成，目标路径: {dst_path}')
        return True
    except Exception as e:
        logger.error(f'移动文件时出错: {e}')
        return None


import time

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
            '--model-type', 'whisper',
            '--model-size', 'large-v3-turbo',
            '--prompt', prompt,
            '--txt',
            '--hide-gui',
            audio_path
        ]
        
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



def process_with_prompts(text, api_key, api_type='deepseek', max_workers=4):
    """
    读取prompts文件夹中的提示词文件并调用AI处理
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        api_type (str): API类型，支持'deepseek'和'claude'
        max_workers (int): 最大线程数，默认为4
    
    Returns:
        bool: 处理是否成功
    """
    try:
        start_time = time.time()
        logger.info(f'开始处理提示词文件，使用{max_workers}个线程')
        
        # 确保prompts和output目录存在
        prompts_dir = 'prompts'
        output_dir = 'output'
        for dir_path in [prompts_dir, output_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.debug(f'创建目录: {dir_path}')
        
        # 获取prompts目录下的所有txt文件
        prompt_files = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        if not prompt_files:
            logger.warning('prompts目录中没有找到txt文件')
            return None
        
        def process_single_prompt(prompt_file):
            try:
                # 读取提示词文件内容
                prompt_path = os.path.join(prompts_dir, prompt_file)
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt = f.read().strip()
                
                # 调用AI处理
                logger.debug(f'线程开始处理提示词文件: {prompt_file}')
                result = call_ai_api(text, api_key, prompt, api_type)
                
                if result:
                    # 保存处理结果
                    output_path = os.path.join(output_dir, prompt_file)
                    if save_text_to_file(result, output_path):
                        logger.debug(f'线程已保存处理结果到: {output_path}')
                        return True
                    else:
                        logger.error(f'线程保存处理结果失败: {output_path}')
                        return None
                else:
                    logger.error(f'线程处理文件失败: {prompt_file}')
                    return None
            
            except Exception as e:
                logger.error(f'线程处理提示词文件时出错 {prompt_file}: {e}')
                return None
        
        # 使用线程池并行处理提示词文件
        success_count = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务并获取future对象
            future_dict = {executor.submit(process_single_prompt, prompt_file): prompt_file 
                         for prompt_file in prompt_files}
            
            # 等待所有任务完成并收集结果
            for future in as_completed(future_dict):
                prompt_file = future_dict[future]
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    logger.error(f'获取任务结果时出错 {prompt_file}: {e}')
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f'所有提示词处理完成，成功处理{success_count}/{len(prompt_files)}个文件，总耗时: {elapsed_time:.2f}秒')
        
        return success_count > 0
    
    except Exception as e:
        logger.error(f'处理提示词文件过程出错: {e}')
        return None


# prompt 将以下音频转写成中文文本。这段音频是关于人工智能的技术讨论。演讲者可能会使用“深度学习”、“自然语言处理”和“强化学习”等术语。请提供清晰准确的转写文本，并确保使用正确的标点符号。
#transcribe_audio('/Users/raidriarb/Downloads/test.m4a','',8)

preprocess_video('/Users/raidriarb/Downloads/test.m4a')
