from dotenv import load_dotenv
import os

# 加载.env文件
load_dotenv()

# API配置
# API密钥
API_KEY = os.getenv('API_KEY', 'sk-a02af37b9800413db3324d34f01f291f')

# API类型，可选值：'deepseek'或'claude'
API_TYPE = os.getenv('API_TYPE', 'deepseek')

''' 选择用于语音转写的模型大小（初次需要下载）
- tiny 75MB
- base 145MB
- small 483.6MB
- medium 1.53GB
- large-v3-turbo 1.62GB
'''
TRANS_MODEL_SIZE = os.getenv('TRANS_MODEL_SIZE', 'large-v3-turbo')


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


'''选用的语音转写模型
whispercpp fasterwhisper whisper
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