import os
import time
import logging
import torch
import config
from .errors import Codes, format_message

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

def normalize_model_type(value):
    if not value:
        return None
    value = str(value).strip().lower()
    if value in ("whisper", "paraformer"):
        return value
    return None

def normalize_optional(value):
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return value

def transcribe_audio(audio_path, prompt, model_type=None, model_size=None, device_mode=None):
    """
    使用 whisper 或 paraformer 进行音频转写，并将结果保存到文本文件中

    参数:
        audio_path (str): 音频文件路径
        prompt (str): 转写提示词，将作为初始提示传入模型
        model_type (str): 模型类型（whisper / paraformer），为空则使用 config
        model_size (str): 模型大小或模型名称（不同模型类型含义不同）
        device_mode (str): cpu / gpu，为空则使用 config
    
    返回:
        str or None: 转写成功时返回保存转写结果的文件名，失败时返回 None
    """
    try:
        # 将相对路径转换为绝对路径，并检查文件是否存在
        audio_path = os.path.abspath(audio_path)
        if not os.path.exists(audio_path):
            logger.error(format_message(Codes.INPUT_NOT_FOUND, f"输入文件不存在: {audio_path}"))
            return None

        logger.info(f"开始音频转写，输入文件路径: {audio_path}")
        start_time = time.time()

        # 获取模型名称、类型和设备（可在 config 中配置，否则使用默认值）
        config_model_type = normalize_model_type(getattr(config, "TRANS_MODEL_TYPE", "whisper"))
        effective_model_type = normalize_model_type(model_type) or config_model_type or "whisper"
        effective_model_size = model_size or getattr(config, "TRANS_MODEL_SIZE", "medium")
        if effective_model_type == "paraformer" and not model_size and config_model_type != "paraformer":
            effective_model_size = "paraformer-zh"
        effective_device_mode = device_mode or getattr(config, "TRANS_DEVICE", "cpu")

        device = get_device(effective_device_mode)
        device_str = "cpu"
        if device.type == "cuda":
            device_str = str(device)

        if effective_model_type == "whisper":
            import whisper

            logger.info(f"加载模型: whisper-{effective_model_size}，使用设备: {device}")
            model_load_start = time.time()
            model = whisper.load_model(effective_model_size).to(device)
            model_load_time = time.time() - model_load_start
            logger.info(f"模型加载完成，耗时: {model_load_time:.2f} 秒")

            # 调用模型进行转写，传入初始提示词（如果模型支持该参数）
            transcribe_start = time.time()
            logger.debug(f"转写的音频路径：{audio_path}")
            result = model.transcribe(audio_path, initial_prompt=prompt)

            transcribe_time = time.time() - transcribe_start
            transcription_text = result.get("text", "").strip()
        elif effective_model_type == "paraformer":
            try:
                from funasr import AutoModel
            except Exception as e:
                logger.error(format_message(Codes.TRANSCRIBE_FAIL, "FunASR 未安装或不可用", str(e)))
                return None

            vad_model = normalize_optional(getattr(config, "TRANS_PARA_VAD_MODEL", "fsmn-vad"))
            punc_model = normalize_optional(getattr(config, "TRANS_PARA_PUNC_MODEL", "ct-punc"))
            batch_size_s = int(getattr(config, "TRANS_PARA_BATCH_SIZE_S", 300))

            if prompt:
                logger.info("Paraformer 不支持 initial_prompt，已忽略该提示词。")

            logger.info(
                f"加载模型: paraformer({effective_model_size})，使用设备: {device_str}，vad={vad_model or 'off'}，punc={punc_model or 'off'}"
            )
            model_load_start = time.time()
            model = AutoModel(
                model=effective_model_size,
                vad_model=vad_model,
                punc_model=punc_model,
                device=device_str,
                disable_update=True,
            )
            model_load_time = time.time() - model_load_start
            logger.info(f"模型加载完成，耗时: {model_load_time:.2f} 秒")

            transcribe_start = time.time()
            logger.debug(f"转写的音频路径：{audio_path}")
            result = model.generate(input=audio_path, batch_size_s=batch_size_s)
            transcribe_time = time.time() - transcribe_start

            if isinstance(result, list) and result and isinstance(result[0], dict):
                transcription_text = result[0].get("text", "").strip()
            else:
                transcription_text = str(result).strip()
        else:
            logger.error(format_message(Codes.INVALID_ARGS, f"不支持的模型类型: {effective_model_type}"))
            return None

        # 构造输出文件名（与输入文件同目录，文件名添加 _transcribed 后缀）
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        output_file = os.path.join(os.path.dirname(audio_path), f"{base_name}_转写.md")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(transcription_text)

        elapsed_time = time.time() - start_time
        logger.info(f"音频转写完成，总耗时: {elapsed_time:.2f} 秒，转写耗时: {transcribe_time:.2f} 秒，结果保存在: {output_file}")
        return output_file

    except Exception as e:
        logger.error(format_message(Codes.TRANSCRIBE_FAIL, "执行音频转写时发生错误", str(e)))
        return None
