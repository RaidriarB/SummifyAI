import os
import time
import logging
import whisper
import torch
import config

logger = logging.getLogger(__name__)

def get_device(mode):
    """
    根据 mode 选择设备，支持 "cpu" 或 "gpu"
    """
    if mode == "cpu":
        return torch.device("cpu")
    elif mode == "gpu":
        if torch.cuda.is_available():
            return torch.device("cuda")
        elif torch.backends.mps.is_available() and torch.backends.mps.is_built():
            return torch.device("mps")
        else:
            return torch.device("cpu")
    else:
        raise ValueError("mode must be 'cpu' or 'gpu'")

def transcribe_audio(audio_path, prompt):
    """
    使用 whisper 库进行音频转写，并将结果保存到文本文件中

    参数:
        audio_path (str): 音频文件路径
        prompt (str): 转写提示词，将作为初始提示传入模型
    
    返回:
        str or None: 转写成功时返回保存转写结果的文件名，失败时返回 None
    """
    try:
        # 将相对路径转换为绝对路径，并检查文件是否存在
        audio_path = os.path.abspath(audio_path)
        if not os.path.exists(audio_path):
            logger.error(f"输入文件不存在: {audio_path}")
            return None

        logger.info(f"开始音频转写，输入文件路径: {audio_path}")
        start_time = time.time()

        # 获取模型名称和设备（可在 config 中配置，否则使用默认值）
        model_size = getattr(config, "TRANS_MODEL_SIZE", "medium")
        device_mode = getattr(config, "TRANS_DEVICE", "cpu")

        device = get_device(device_mode)

        # Whisper
        logger.info(f"加载模型: whisper-{model_size}，使用设备: {device}")
        model_load_start = time.time()
        model = whisper.load_model(model_size).to(device)
        model_load_time = time.time() - model_load_start
        logger.info(f"模型加载完成，耗时: {model_load_time:.2f} 秒")

        # 调用模型进行转写，传入初始提示词（如果模型支持该参数）
        transcribe_start = time.time()
        logger.debug(f"转写的音频路径：{audio_path}")
        result = model.transcribe(audio_path, initial_prompt=prompt)

        transcribe_time = time.time() - transcribe_start

        transcription_text = result.get("text", "").strip()

        # 构造输出文件名（与输入文件同目录，文件名添加 _transcribed 后缀）
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_file = os.path.join(os.path.dirname(audio_path), f"{base_name}_转写.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcription_text)

        elapsed_time = time.time() - start_time
        logger.info(f"音频转写完成，总耗时: {elapsed_time:.2f} 秒，转写耗时: {transcribe_time:.2f} 秒，结果保存在: {output_file}")
        return output_file

    except Exception as e:
        logger.error(f"执行音频转写时发生错误: {e}")
        return None
