import logging
from openai import OpenAI
import anthropic
import config

logger = logging.getLogger(__name__)

def _call_deepseek_api(text, api_key, prompt):
    """
    调用DeepSeek API进行文本处理
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        prompt (str): 提示词
        
    Returns:
        str: API返回的处理结果
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=config.MODEL_MAX_TOKENS,
        temperature=config.MODEL_TEMPERATURE,
        stream=False
    )
    return response.choices[0].message.content

def _call_claude_api(text, api_key, prompt):
    """
    调用Claude API进行文本处理
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        prompt (str): 提示词
        
    Returns:
        str: API返回的处理结果
    """
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-3.5-Sonnet",
        max_tokens=config.MODEL_MAX_TOKENS,
        temperature=config.MODEL_TEMPERATURE,
        system=prompt,
        messages=[
            {"role": "user", "content": text}
        ]
    )
    return response.content[0].text

def _call_openai_api(text, api_key, prompt):
    """
    调用OpenAI (ChatGPT) API进行文本处理
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        prompt (str): 提示词
        
    Returns:
        str: API返回的处理结果
    """
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",  # 默认使用GPT-4o模型，可根据需要调整
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text}
        ],
        max_tokens=config.MODEL_MAX_TOKENS,
        temperature=config.MODEL_TEMPERATURE
    )
    return response.choices[0].message.content

def call_ai_api(text, api_key, prompt, api_type='deepseek'):
    """
    调用AI API进行文本处理，支持DeepSeek、Claude和OpenAI
    
    Args:
        text (str): 要处理的文本
        api_key (str): API密钥
        prompt (str): 提示词
        api_type (str): API类型，支持'deepseek'、'claude'和'openai'
    
    Returns:
        str: API返回的处理结果
    """
    try:
        logger.debug(f'开始调用AI API，类型: {api_type}，输入文本长度: {len(text)}')
        
        if api_type == 'deepseek':
            result = _call_deepseek_api(text, api_key, prompt)
        elif api_type == 'claude':
            result = _call_claude_api(text, api_key, prompt)
        elif api_type == 'openai':
            result = _call_openai_api(text, api_key, prompt)
        else:
            logger.error(f'不支持的API类型: {api_type}')
            return None
        
        logger.debug(f'API调用成功，返回内容长度: {len(result) if result else 0}')
        return result
    except Exception as e:
        logger.error(f"调用API时出错: {e}")
        return None