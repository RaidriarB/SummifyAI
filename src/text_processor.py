import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


import config
from .ai_service import call_ai_api
from .utils import save_text_to_file,split_text_into_chunks
from .errors import Codes, format_message

logger = logging.getLogger(__name__)

def add_punctuation(text, api_key, prompt, chunk_size=2000, api_type='deepseek'):
    """
    对文本进行分块并调用AI API添文本修正润色
    
    Args:
        text (str): 原始文本
        api_key (str): API密钥
        prompt (str): 提示词
        chunk_size (int): 分块大小
        api_type (str): API类型，支持'deepseek'和'claude'
    
    Returns:
        str: 带有标点的完整文本
    """
    
    logger.debug(f'开始添文本修正润色，输入文本长度: {len(text)}，分块大小: {chunk_size}')
    
    # 确保temp目录存在
    temp_dir =  os.path.join(config.TEMP_DIR, 'split')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)


    chunks = split_text_into_chunks(text, chunk_size)
    if not chunks:
        logger.warning(format_message(Codes.AI_CALL_FAIL, '文本为空或无法分块，跳过处理'))
        return ""
    
    # 使用简单的空格分割方法
    # sentences = text.split(' ')
    # chunks = []
    # current_chunk = ''
    # for sentence in sentences:
    #     if len(current_chunk) + len(sentence) + 1 <= chunk_size:  # +1 for the space
    #         current_chunk += ('' if not current_chunk else ' ') + sentence
    #     else:
    #         if current_chunk:
    #             chunks.append(current_chunk)
    #         current_chunk = sentence
    # if current_chunk:
    #     chunks.append(current_chunk)
    
    # 保存原始分块
    for idx, chunk in enumerate(chunks):
        chunk_file = os.path.join(temp_dir, f'chunk_{idx}_original.txt')
        save_text_to_file(chunk, chunk_file)
        logger.debug(f'保存原始分块 {idx} 到文件: {chunk_file}')
    
    # 使用线程池并行处理每个分块，使用字典保存顺序
    results_dict = {}
    errors = []
    with ThreadPoolExecutor(max_workers=config.AI_THREADS) as executor:
        # 为每个分块创建带索引的future
        future_dict = {
            executor.submit(call_ai_api, chunk, api_key, prompt, api_type): idx
            for idx, chunk in enumerate(chunks)
        }
        
        # 等待所有future完成并按索引保存结果
        for future in as_completed(future_dict):
            idx = future_dict[future]
            try:
                processed_text = future.result()
            except Exception as e:
                errors.append((idx, str(e)))
                logger.error(format_message(Codes.AI_CALL_FAIL, f'分块 {idx} 处理失败', str(e)))
                continue
            if not processed_text:
                errors.append((idx, 'empty result'))
                logger.error(format_message(Codes.AI_CALL_FAIL, f'分块 {idx} 处理失败', '返回为空'))
                continue
            results_dict[idx] = processed_text
            # 保存处理后的分块
            processed_file = os.path.join(temp_dir, f'chunk_{idx}_processed.txt')
            save_text_to_file(processed_text, processed_file)
            logger.debug(f'保存处理后分块 {idx} 到文件: {processed_file}')
    
    # 按照原始顺序拼接结果
    if errors or len(results_dict) != len(chunks):
        logger.error(format_message(
            Codes.AI_CALL_FAIL,
            f'文本修正润色失败，成功 {len(results_dict)}/{len(chunks)}，错误数: {len(errors)}'
        ))
        return None

    ordered_results = [results_dict[i] for i in range(len(chunks))]
    return "".join(ordered_results)


def process_with_prompts(text, api_key, api_type='deepseek',prompts_dir='prompts',output_dir='output'):
    """
    读取prompts文件夹中的提示词文件并调用AI处理
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        api_type (str): API类型，支持'deepseek'和'claude'
    
    Returns:
        bool: 处理是否成功
    """
    max_workers = config.AI_THREADS

    try:
        start_time = time.time()
        logger.info(f'开始处理提示词文件，使用{max_workers}个线程')
        
        # 确保prompts和output目录存在
        #prompts_dir = 'prompts'
        #output_dir = 'output'
        for dir_path in [prompts_dir, output_dir]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.debug(f'创建目录: {dir_path}')
        
        # 获取prompts目录下的所有txt文件
        prompt_files = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
        if not prompt_files:
            logger.warning(format_message(Codes.PROMPT_MISSING, 'prompts目录中没有找到txt文件'))
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
                    base_name = os.path.splitext(prompt_file)[0]
                    output_path = os.path.join(output_dir, f"{base_name}.md")
                    if save_text_to_file(result, output_path):
                        logger.debug(f'线程已保存处理结果到: {output_path}')
                        return True
                    else:
                        logger.error(format_message(Codes.FILE_IO, f'线程保存处理结果失败: {output_path}'))
                        return None
                else:
                    logger.error(format_message(Codes.AI_CALL_FAIL, f'线程处理文件失败: {prompt_file}'))
                    return None
            
            except Exception as e:
                logger.error(format_message(Codes.AI_CALL_FAIL, f'线程处理提示词文件时出错 {prompt_file}', str(e)))
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
                    logger.error(format_message(Codes.AI_CALL_FAIL, f'获取任务结果时出错 {prompt_file}', str(e)))
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f'所有提示词处理完成，成功处理{success_count}/{len(prompt_files)}个文件，总耗时: {elapsed_time:.2f}秒')
        
        return success_count > 0
    
    except Exception as e:
        logger.error(format_message(Codes.AI_CALL_FAIL, '处理提示词文件过程出错', str(e)))
        return None
