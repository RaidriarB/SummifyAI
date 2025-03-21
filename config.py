# API配置
# Claude API密钥
API_KEY = "你的api"

# API类型，可选值：'deepseek'或'claude'
API_TYPE = 'deepseek'




############################
#     高级设置，请谨慎修改！  #
############################

# 如果上传给AI的内容超过这个长度，会被分块
CHUNK_SIZE=4000

MODEL_TEMPERATURE=0.9
MODEL_MAX_TOKENS=8000
AI_THREADS = 4


'''选用的语音转写模型
buzz cli manual:
  -m, --model-type <model-type>  Model type. Allowed: whisper, whispercpp,
                                 huggingface, fasterwhisper, openaiapi. Default:
                                 whisper.
'''
TRANS_MODEL_TYPE = 'whisper'


'''模型大小
buzz cli manual:
  -s, --model-size <model-size>  Model size. Use only when --model-type is
                                 whisper, whispercpp, or fasterwhisper. Allowed:
                                 tiny, base, small, medium, large. Default:
                                 tiny.
'''

TRANS_MODEL_SIZE = 'large-v3-turbo'

TRANS_THREADS = 4



# 数据临时文件夹
TEMP_DIR = 'tempdata'