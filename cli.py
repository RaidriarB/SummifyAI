#!/usr/bin/env python3
import argparse
import os
import logging

from src.video_processor import preprocess_video
from src.transcription import transcribe_audio
from src.text_processor import add_punctuation, process_with_prompts
from src.utils import save_text_to_file, move_file, copy_file
from src.ai_service import call_ai_api

import config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

VERSION = 'v1.3.0'
AUTHOR = 'RaidriarB'


def parse_steps(steps_str):
    """
    解析用户输入的步骤字符串
    
    Args:
        steps_str (str): 用户输入的步骤字符串，如 '01234'
    
    Returns:
        list: 要执行的步骤列表
    """
    valid_steps = set('01234')
    steps = [int(s) for s in steps_str if s in valid_steps]
    return sorted(list(dict.fromkeys(steps)))  # 去重并保持顺序

def print_banner():
    banner = f"""
    ███████╗██╗   ██╗███╗   ███╗███╗   ███╗██╗███████╗██╗   ██╗ █████╗ ██╗
    ██╔════╝██║   ██║████╗ ████║████╗ ████║██║██╔════╝╚██╗ ██╔╝██╔══██╗██║
    ███████╗██║   ██║██╔████╔██║██╔████╔██║██║█████╗   ╚████╔╝ ███████║██║
    ╚════██║██║   ██║██║╚██╔╝██║██║╚██╔╝██║██║██╔══╝    ╚██╔╝  ██╔══██║██║
    ███████║╚██████╔╝██║ ╚═╝ ██║██║ ╚═╝ ██║██║██║        ██║   ██║  ██║██║
    ╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚═╝╚═╝╚═╝        ╚═╝   ╚═╝  ╚═╝╚═╝
                                                                {VERSION}
    智能音视频内容总结工具 - 让知识传播更高效  by {AUTHOR}
    """
    print(banner)

def main():
    
    parser = argparse.ArgumentParser(
        description='''
    音频处理工具 - 将音视频内容转换为文字并进行智能总结

    示例用法：
    1. 处理视频文件（执行所有步骤）：
        python cli.py -i video.mp4

    2. 处理音频文件并指定输出目录：
        python cli.py -i podcast.mp3 --output-dir my_summary

    3. 只执行音频预处理和语音转写：
        python cli.py -i lecture.wav --steps 12

    4. 从已有的转写文本开始处理：
        python cli.py -i transcript.txt --steps 34
        ''',
    formatter_class=argparse.RawTextHelpFormatter  # 保留换行
    )
    parser.add_argument('-i','--input', 
                      help='''
输入文件路径。支持的格式：
- 视频文件：mp4, avi, mkv等
- 音频文件：mp3, wav, m4a等
- 文本文件：txt（仅用于步骤3和4）
                      ''')
    parser.add_argument('-s','--steps', 
                      default='1234', 
                      help='''
要执行的步骤（默认：1234）：
1: 音频预处理 - 从视频/音频中提取音轨
2: 语音转写 - 将音频转换为文字
3: AI优化转写 - 优化文本的可读性
4: AI总结 - 生成多个维度的内容总结
注意：步骤必须按顺序执行，如"12"、"234"
                      ''')
    parser.add_argument('-o','--output-dir', 
                      default='output', 
                      help='''
输出目录，用于存放处理结果（默认：output）
每个步骤的结果将保存在该目录下
                      ''')

    parser.add_argument('--prompts-dir',
                      default='prompts',
                      help='''
提示词文件目录路径（默认：prompts）
用于存放AI总结时使用的提示词文件
                      ''')

    parser.add_argument('--nobanner',
                      action='store_true',
                      default=False,
                      help="不输出Banner")
    
    args = parser.parse_args()


    if not args.nobanner: print_banner()
    
    # 确保输入文件存在
    if not os.path.exists(args.input):
        logger.error(f'输入文件不存在: {args.input}')
        return
    
    # 确保输出目录存在
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # 解析要执行的步骤
    steps = parse_steps(args.steps)
    logger.info(f'将执行以下步骤: {steps}')
    
    current_file = args.input
    base_name = os.path.splitext(os.path.basename(args.input))[0]
    
    try:

        # 步骤1：音频预处理
        if 1 in steps:
            logger.info('步骤1：开始音频预处理')
            processed_audio = preprocess_video(current_file)
            if not processed_audio:
                logger.error('音频预处理失败')
                return
            current_file = processed_audio
            # 移动到data/1目录
            data_file = os.path.join(config.TEMP_DIR, '1', os.path.basename(current_file))
            if not move_file(current_file, data_file):
                logger.error('移动预处理结果失败')
                return
            current_file = data_file
            
            # 如果步骤1是最后一步，将结果复制到output目录
            if steps[-1] == 1:
                output_file = os.path.join(args.output_dir, os.path.basename(current_file))
                if not copy_file(current_file, output_file):
                    logger.error('复制预处理结果到output目录失败')
                    return
        
        # 步骤2：语音转写
        if 2 in steps:
            logger.info('步骤2：开始语音转写')
            prompt = '将以下音频转写成中文文本,确保使用正确的标点符号。'
            transcribed_file = transcribe_audio(current_file, prompt)
            if not transcribed_file:
                logger.error('语音转写失败')
                return
            
            current_file = os.path.join(os.path.dirname(current_file), transcribed_file)
            # 移动到data/2目录
            data_file = os.path.join(config.TEMP_DIR, '2', os.path.basename(current_file))
            if not move_file(current_file, data_file):
                logger.error('移动转写结果失败')
                return
            current_file = data_file
            
            # 如果步骤2是最后一步，将结果复制到output目录
            if steps[-1] == 2:
                output_file = os.path.join(args.output_dir, os.path.basename(current_file))
                if not copy_file(current_file, output_file):
                    logger.error('复制转写结果到output目录失败')
                    return
        
        # 步骤3：AI文本修正润色
        if 3 in steps:
            logger.info('步骤3：开始AI文本修正润色')
            api_key = config.API_KEY
            if not api_key:
                logger.error('未配置API密钥')
                return
            
            with open(current_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            prompt =  '''
            我通过语音转写，把一篇文本转换为了文字稿，然后分成了一些小部分。请你帮我添文本修正润色，并且改正语句中的偶尔转换错误。
            你可以适当的给文本分段处理。
            注意！必须忠实于文本，语句可能是被截取的、不完整的，禁止自己发挥，续写额外内容。
            只需要回复我最终结果即可。
            '''
            punctuated_text = add_punctuation(
                text,
                api_key,
                prompt,
                config.CHUNK_SIZE,
                config.API_TYPE
            )
            
            if punctuated_text:
                punctuated_file = os.path.join(args.output_dir, f'{base_name}_fixed.txt')
                if save_text_to_file(punctuated_text, punctuated_file):
                    current_file = punctuated_file
                    # 保存到data/3目录
                    data_file = os.path.join(config.TEMP_DIR, '3', os.path.basename(current_file))
                    if not copy_file(current_file, data_file):
                        logger.error('保存文本修正润色结果失败')
                        return
                    
                    # 如果步骤3是最后一步，将结果复制到output目录?
                    # 无需这样做，因为步骤3的结果已经被输出到output目录
                else:
                    logger.error('保存文本修正润色文本失败')
                    return
            else:
                logger.error('AI文本修正润色失败')
                return
        
        # 步骤4：AI总结
        if 4 in steps:
            logger.info('步骤4：开始AI总结')
            api_key = config.API_KEY
            if not api_key:
                logger.error('未配置API密钥')
                return
            
            with open(current_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not process_with_prompts(text, api_key, config.API_TYPE, args.prompts_dir, args.output_dir):
                logger.error('AI总结失败')
                return
        
        logger.info('所有步骤处理完成')
        
    except Exception as e:
        logger.error(f'处理过程出错: {e}')

if __name__ == '__main__':
    main()