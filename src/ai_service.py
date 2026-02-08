import logging
import time
from openai import OpenAI
import config
from .errors import Codes, format_message

logger = logging.getLogger(__name__)

def _sleep_with_backoff(attempt):
    backoff = config.AI_RETRY_BACKOFF_SECONDS * (2 ** attempt)
    time.sleep(backoff)

def _call_with_retries(fn, api_type):
    last_error = None
    for attempt in range(config.AI_RETRY_MAX + 1):
        try:
            return fn()
        except Exception as e:
            last_error = e
            if attempt >= config.AI_RETRY_MAX:
                break
            logger.warning(format_message(Codes.AI_CALL_FAIL, f'调用{api_type}失败，准备重试({attempt + 1}/{config.AI_RETRY_MAX})', str(e)))
            _sleep_with_backoff(attempt)
    raise last_error

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
        model=config.DEEPSEEK_MODEL,
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
    try:
        import anthropic
    except Exception as e:
        raise RuntimeError("未安装 anthropic 依赖，无法使用 Claude API") from e

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=config.CLAUDE_MODEL,
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
        model=config.OPENAI_MODEL,  # 默认使用GPT-4o模型，可根据需要调整
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

        if not api_key:
            logger.error(format_message(Codes.AI_KEY_MISSING, 'API密钥为空'))
            return None

        def _call():
            if api_type == 'deepseek':
                return _call_deepseek_api(text, api_key, prompt)
            if api_type == 'claude':
                return _call_claude_api(text, api_key, prompt)
            if api_type == 'openai':
                return _call_openai_api(text, api_key, prompt)
            raise ValueError(f'不支持的API类型: {api_type}')

        result = _call_with_retries(_call, api_type)
        logger.debug(f'API调用成功，返回内容长度: {len(result) if result else 0}')
        return result
    except Exception as e:
        logger.error(format_message(Codes.AI_CALL_FAIL, '调用API时出错', str(e)))
        return None
