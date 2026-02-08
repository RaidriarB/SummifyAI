import os
import logging
import shutil
import re
from .errors import Codes, format_message

logger = logging.getLogger(__name__)

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
        logger.error(format_message(Codes.FILE_IO, '保存文本到文件时出错', str(e)))
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
        shutil.copy2(src_path, dst_path)
        logger.debug(f'文件复制完成，目标路径: {dst_path}')
        return True
    except Exception as e:
        logger.error(format_message(Codes.FILE_IO, '复制文件时出错', str(e)))
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
        shutil.move(src_path, dst_path)
        logger.debug(f'文件移动完成，目标路径: {dst_path}')
        return True
    except Exception as e:
        logger.error(format_message(Codes.FILE_IO, '移动文件时出错', str(e)))
        return None




def split_text_into_chunks(text, chunk_size):
    # 统一的正则表达式：
    # .+? —— 非贪婪匹配任意字符
    # (?:\s*[，。！？；：,.!?;:]+\s*|\s+|$)
    #    —— 匹配以下三种情况之一：
    #         1. 可选空白 + 至少一个标点符号 + 可选空白
    #         2. 一个或多个空白符（不含标点）
    #         3. 文本结尾
    pattern = re.compile(r'.+?(?:\s*[，。！？；：,.!?;:]+\s*|\s+|$)')
    
    # 利用正则表达式提取各个分段
    sentences = [s for s in pattern.findall(text) if s.strip()]
    
    chunks = []
    current_chunk = ""
    for sentence in sentences:
        #print("[" + sentence + "]")
        candidate = (current_chunk  + sentence) if current_chunk else sentence
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk:
        chunks.append(current_chunk)
    return chunks
