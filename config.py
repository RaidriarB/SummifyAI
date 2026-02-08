from dotenv import load_dotenv
import os

# 加载.env文件
load_dotenv()

# API配置
# API密钥（建议通过环境变量或 .env 文件配置）
API_KEY = os.getenv('API_KEY', '')

# API类型，可选值：'deepseek'、'claude'或'openai'
API_TYPE = os.getenv('API_TYPE', 'deepseek').lower()

# 可选：模型名称覆盖
DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3.5-Sonnet')

''' 选择用于语音转写的模型大小（初次需要下载）
- tiny 75MB
- base 145MB
- small 483.6MB
- medium 1.53GB
- large-v3-turbo 1.62GB
'''
TRANS_MODEL_SIZE = os.getenv('TRANS_MODEL_SIZE', 'large-v3-turbo')

'''
选择语音转写模型类型
whisper 或 paraformer
'''
TRANS_MODEL_TYPE = os.getenv('TRANS_MODEL_TYPE', 'whisper').lower()

# Paraformer 默认配置
TRANS_PARA_VAD_MODEL = os.getenv('TRANS_PARA_VAD_MODEL', 'fsmn-vad')
TRANS_PARA_PUNC_MODEL = os.getenv('TRANS_PARA_PUNC_MODEL', 'ct-punc')
TRANS_PARA_BATCH_SIZE_S = int(os.getenv('TRANS_PARA_BATCH_SIZE_S', '300'))


############################
#     高级设置，请谨慎修改！  #
############################

'''
如果上传给AI的内容超过这个长度，会被分块。注意这是字符串长度，不是token数量
'''
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '4000'))

MODEL_TEMPERATURE = float(os.getenv('MODEL_TEMPERATURE', '0.9'))
MODEL_MAX_TOKENS = int(os.getenv('MODEL_MAX_TOKENS', '8000'))
AI_THREADS = int(os.getenv('AI_THREADS', '4'))
AI_RETRY_MAX = int(os.getenv('AI_RETRY_MAX', '2'))
AI_RETRY_BACKOFF_SECONDS = float(os.getenv('AI_RETRY_BACKOFF_SECONDS', '1.0'))

# 日志配置
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', '5000000'))
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '3'))


'''选用的语音转写模型
whisper 或 paraformer
'''
# TODO 未来再支持faster-whisper
# whisper已经很好用，而faster-whisper只支持cuda mode，Macbook M系列和windows都不太适合
# whisper直接cpu mode跑就可以了
# TRANS_MODEL_TYPE = 'whisper'


'''cpu or gpu
gpu需要cuda，未必支持，请自行确认。
Macbook M系列，不管是whisper还是faster-whisper都不能gpu模式
'''
TRANS_DEVICE = os.getenv('TRANS_DEVICE', 'cpu')


# 数据临时文件夹
TEMP_DIR = os.getenv('TEMP_DIR', 'tempdata')
