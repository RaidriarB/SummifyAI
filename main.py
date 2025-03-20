#!/usr/bin/env python3
import argparse
import os,logging
import logging
from audio_processor import (
    preprocess_video,
    add_punctuation,
    process_with_prompts,
    save_text_to_file,
    transcribe_audio,
    move_file,
    copy_file
)
from config import *

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHUNK_SIZE=5000

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

def main():
    parser = argparse.ArgumentParser(description='音频处理工具')
    parser.add_argument('input_file', help='输入文件路径（音频或视频文件）')
    parser.add_argument('--steps', default='1234', help='要执行的步骤（1:音频预处理, 2:语音转写, 3:AI优化转写, 4:AI总结），默认执行所有步骤')
    parser.add_argument('--output-dir', default='output', help='输出目录')
    
    args = parser.parse_args()
    
    # 确保输入文件存在
    if not os.path.exists(args.input_file):
        logger.error(f'输入文件不存在: {args.input_file}')
        return
    
    # 确保输出目录存在
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # 解析要执行的步骤
    steps = parse_steps(args.steps)
    logger.info(f'将执行以下步骤: {steps}')
    
    current_file = args.input_file
    base_name = os.path.splitext(os.path.basename(args.input_file))[0]
    
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
            data_file = os.path.join('tempdata', '1', os.path.basename(current_file))
            if not move_file(current_file, data_file):
                logger.error('移动预处理结果失败')
                return
            current_file = data_file
        
        # 步骤2：语音转写
        if 2 in steps:
            logger.info('步骤2：开始语音转写')
            prompt = '将以下音频转写成中文文本。这段音频是关于人工智能的技术讨论。演讲者可能会使用"深度学习"、"自然语言处理"和"强化学习"等术语。请提供清晰准确的转写文本，并确保使用正确的标点符号。'
            transcribed_file = transcribe_audio(current_file, prompt,n_threads=8)
            if not transcribed_file:
                logger.error('语音转写失败')
                return
            
            current_file = os.path.join(os.path.dirname(current_file), transcribed_file)
            # 移动到data/2目录
            data_file = os.path.join('tempdata', '2', os.path.basename(current_file))
            if not move_file(current_file, data_file):
                logger.error('移动转写结果失败')
                return
            current_file = data_file
        
        # 步骤3：AI加标点
        if 3 in steps:
            logger.info('步骤3：开始AI加标点')
            api_key = DEEPSEEK_API_KEY if API_TYPE == 'deepseek' else CLAUDE_API_KEY
            if not api_key:
                logger.error('未配置API密钥')
                return
            
            with open(current_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            prompt =  '''
            我通过语音转写，把一篇文本转换为了文字稿，然后分成了一些小部分。请你帮我添加标点，并且改正语句中的偶尔转换错误。
            你可以适当的给文本分段处理。
            注意！必须忠实于文本，语句可能是被截取的、不完整的，禁止自己发挥，续写额外内容。
            只需要回复我最终结果即可。
            '''
            punctuated_text = add_punctuation(
                text,
                api_key,
                prompt,
                CHUNK_SIZE,
                API_TYPE
            )
            
            if punctuated_text:
                punctuated_file = os.path.join(args.output_dir, f'{base_name}_fixed.txt')
                if save_text_to_file(punctuated_text, punctuated_file):
                    current_file = punctuated_file
                    # 保存到data/3目录
                    data_file = os.path.join('tempdata', '3', os.path.basename(current_file))
                    if not copy_file(current_file, data_file):
                        logger.error('保存加标点结果失败')
                        return
                else:
                    logger.error('保存加标点文本失败')
                    return
            else:
                logger.error('AI加标点失败')
                return
        
        # 步骤4：AI总结
        if 4 in steps:
            logger.info('步骤4：开始AI总结')
            api_key = DEEPSEEK_API_KEY if API_TYPE == 'deepseek' else CLAUDE_API_KEY
            if not api_key:
                logger.error('未配置API密钥')
                return
            
            with open(current_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not process_with_prompts(text, api_key, API_TYPE):
                logger.error('AI总结失败')
                return
        
        logger.info('所有步骤处理完成')
        
    except Exception as e:
        logger.error(f'处理过程出错: {e}')

if __name__ == '__main__':
    main()