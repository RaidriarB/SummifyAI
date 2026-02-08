from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO
import os
import time
import logging
import subprocess
import json
import sys
import re
from pathlib import Path
from threading import Thread, Lock
from queue import Queue

IS_WINDOWS = os.name == "nt"

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
socketio = SocketIO(app, cors_allowed_origins='*')

ROOT_DIR = Path(__file__).resolve().parents[1]
WEB_DIR = Path(__file__).resolve().parent
sys.path.append(str(ROOT_DIR))

import config
from src.errors import Codes, format_message
from src.logging_config import setup_logging

# 配置文件存储路径
UPLOAD_FOLDER = 'data/upload'
OUTPUT_FOLDER = 'data/output'

# 确保目录存在
os.makedirs(os.path.join(app.root_path, UPLOAD_FOLDER), exist_ok=True)
os.makedirs(os.path.join(app.root_path, OUTPUT_FOLDER), exist_ok=True)

setup_logging(
    app_name="web",
    log_dir=str(ROOT_DIR / config.LOG_DIR),
    level=config.LOG_LEVEL,
    max_bytes=config.LOG_MAX_BYTES,
    backup_count=config.LOG_BACKUP_COUNT,
)
logger = logging.getLogger(__name__)

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

ALLOWED_EXTS = {
    ".mp4", ".avi", ".mkv", ".mov", ".flv", ".webm", ".m4v",
    ".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg",
    ".txt",
}

task_queue = Queue()
worker_lock = Lock()
worker_thread = None


def sanitize_filename(filename):
    if not filename:
        return None
    name = os.path.basename(filename)
    name = name.replace("/", "_").replace("\\", "_").strip()
    if not name:
        return None
    return name


def is_valid_steps(steps):
    if not steps:
        return False
    if any(s not in "1234" for s in steps):
        return False
    ordered = []
    for s in steps:
        if s not in ordered:
            ordered.append(s)
    return ordered == sorted(ordered)


def is_allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTS


def ensure_unique_path(directory, filename):
    base, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1
    while os.path.exists(os.path.join(directory, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1
    return candidate


def clean_output_line(line):
    if line is None:
        return ""
    line = ANSI_ESCAPE_RE.sub("", line)
    return line.replace("\r", "").strip()


def should_skip_output(line):
    if not line:
        return True
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("0% ") or stripped.startswith("100% "):
        return True
    if "it/s" in stripped:
        return True
    if "rtf_avg" in stripped:
        return True
    if "time_speech" in stripped and "time_escape" in stripped:
        return True
    if "load_data" in stripped and "extract_feat" in stripped and "forward" in stripped:
        return True
    if stripped.startswith("{'load_data'") or stripped.startswith('{"load_data"'):
        return True
    return False


def task_worker():
    while True:
        filename, steps, model_type, model_size = task_queue.get()
        try:
            transcribe_task(filename, steps, model_type, model_size)
        finally:
            task_queue.task_done()

def enqueue_task(filename, steps, model_type=None, model_size=None):
    global worker_thread
    task_queue.put((filename, steps, model_type, model_size))
    with worker_lock:
        if worker_thread is None or not worker_thread.is_alive():
            worker_thread = Thread(target=task_worker, daemon=True)
            worker_thread.start()


def get_files_info():
    upload_dir = os.path.join(app.root_path, UPLOAD_FOLDER)

    records = load_transcription_records()
    file_records = {}
    for record in records.get('records', []):
        if not isinstance(record, dict):
            continue
        filename = record.get('file_name')
        if not isinstance(filename, str) or not filename.strip():
            continue
        file_records[filename] = record

    # 回填缺失记录（避免老文件不显示）
    if os.path.exists(upload_dir):
        for file in os.listdir(upload_dir):
            if not is_allowed_file(file):
                continue
            if file.endswith("_转写.txt"):
                continue
            if file not in file_records:
                update_transcription_record(file, created_time=time.strftime('%Y-%m-%d %H:%M:%S'))
                file_records[file] = {
                    'file_name': file,
                    'transcribed': False,
                    'last_transcription_time': None,
                    'created_time': time.strftime('%Y-%m-%d %H:%M:%S'),
                }

    files_info = []
    for file, record in file_records.items():
        if not isinstance(file, str):
            continue
        if not os.path.exists(os.path.join(upload_dir, file)):
            continue
        created_time = record.get('created_time') or time.strftime('%Y-%m-%d %H:%M:%S')
        files_info.append({
            'name': file,
            'transcribed': record.get('transcribed', False),
            'last_time': record.get('last_transcription_time') or '未转写',
            'created_time': created_time
        })

    files_info.sort(key=lambda x: x['created_time'] or '', reverse=True)
    return files_info


@app.route('/test')
def test():
    return render_template('test.html')

@app.route('/')
def index():
    return render_template('index.html', files=get_files_info())


@app.route('/files')
def list_files():
    return jsonify({'status': 'success', 'code': Codes.SUCCESS, 'files': get_files_info()})

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': 'URL不能为空'})
    
    from crawler import download_media
    upload_dir = os.path.join(app.root_path, UPLOAD_FOLDER)
    master_fd = None
    try:
        filename = download_media(url, upload_dir)
        if filename:
            # 记录文件创建时间
            update_transcription_record(filename, created_time=time.strftime('%Y-%m-%d %H:%M:%S'))
            socketio.emit('download_progress', {'status': 'success', 'code': Codes.SUCCESS, 'message': f'文件 {filename} 下载成功'})
            return jsonify({'status': 'success', 'code': Codes.SUCCESS, 'message': f'文件 {filename} 下载成功'})
        else:
            socketio.emit('download_progress', {'status': 'error', 'code': Codes.DOWNLOAD_FAIL, 'message': '下载失败'})
            logger.error(format_message(Codes.DOWNLOAD_FAIL, '下载失败', f'url={url}'))
            return jsonify({'status': 'error', 'code': Codes.DOWNLOAD_FAIL, 'message': '下载失败'})
    except Exception as e:
        error_message = str(e)
        socketio.emit('download_progress', {'status': 'error', 'code': Codes.DOWNLOAD_FAIL, 'message': error_message})
        logger.error(format_message(Codes.DOWNLOAD_FAIL, '下载出错', f'url={url} err={e}'))
        return jsonify({'status': 'error', 'code': Codes.DOWNLOAD_FAIL, 'message': error_message})


@app.route('/upload', methods=['POST'])
def upload_files():
    files = request.files.getlist('files')
    steps = request.form.get('steps', '12')
    auto_start = request.form.get('auto_start', '1') == '1'
    model_type = (request.form.get('model_type') or '').strip() or None
    model_size = (request.form.get('model_size') or '').strip() or None

    if not files:
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': '未选择文件'})
    if not is_valid_steps(steps):
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': 'steps 参数不合法'})

    upload_dir = os.path.join(app.root_path, UPLOAD_FOLDER)
    saved = []
    errors = []
    queued = []

    for f in files:
        original_name = f.filename
        safe_name = sanitize_filename(original_name)
        if not safe_name:
            errors.append({'file': original_name, 'code': Codes.INVALID_ARGS, 'message': '文件名无效'})
            continue
        if not is_allowed_file(safe_name):
            errors.append({'file': original_name, 'code': Codes.UNSUPPORTED_INPUT, 'message': '不支持的文件类型'})
            continue

        final_name = ensure_unique_path(upload_dir, safe_name)
        save_path = os.path.join(upload_dir, final_name)
        try:
            f.save(save_path)
            saved.append(final_name)
            update_transcription_record(final_name, created_time=time.strftime('%Y-%m-%d %H:%M:%S'))
            if auto_start:
                enqueue_task(final_name, steps, model_type, model_size)
                queued.append(final_name)
            logger.info(f"上传成功: {final_name}")
        except Exception as e:
            errors.append({'file': original_name, 'code': Codes.UPLOAD_FAIL, 'message': str(e)})
            logger.error(format_message(Codes.UPLOAD_FAIL, '上传失败', f'file={original_name} err={e}'))

    status = 'success' if saved else 'error'
    code = Codes.SUCCESS if saved else Codes.UPLOAD_FAIL
    return jsonify({'status': status, 'code': code, 'saved': saved, 'queued': queued, 'errors': errors})

@app.route('/transcribe', methods=['POST'])
def start_transcribe():
    filename = request.form.get('filename')
    steps = request.form.get('steps', '12')  # 默认只执行转写步骤
    model_type = (request.form.get('model_type') or '').strip() or None
    model_size = (request.form.get('model_size') or '').strip() or None

    if not filename:
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': '未提供文件名'})
    if not is_valid_steps(steps):
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': 'steps 参数不合法'})
    if not os.path.exists(os.path.join(app.root_path, UPLOAD_FOLDER, filename)):
        return jsonify({'status': 'error', 'code': Codes.INPUT_NOT_FOUND, 'message': '文件不存在'})
    
    enqueue_task(filename, steps, model_type, model_size)
    return jsonify({'status': 'success', 'code': Codes.SUCCESS, 'message': '已加入任务队列'})

@app.route('/transcribe/<filename>')
def view_transcription(filename):
    # 获取输出目录路径
    base_name = os.path.splitext(filename)[0]
    file_output_dir = os.path.join(app.root_path, OUTPUT_FOLDER, base_name)
    
    # 获取目录下的所有文件
    files = []
    if os.path.exists(file_output_dir):
        files = [{'name': f} for f in os.listdir(file_output_dir)]
    
    # 获取默认显示的文件内容（优先 _转写.md）
    default_candidates = [
        f'{os.path.splitext(filename)[0]}_音频_转写.md',
        f'{os.path.splitext(filename)[0]}_转写.md',
        f'{os.path.splitext(filename)[0]}_音频_转写.txt',
        f'{os.path.splitext(filename)[0]}_转写.txt',
    ]
    default_file = None
    for candidate in default_candidates:
        if os.path.exists(os.path.join(file_output_dir, candidate)):
            default_file = candidate
            break
    if not default_file and files:
        default_file = files[0]['name']
    content = ''
    if default_file:
        default_file_path = os.path.join(file_output_dir, default_file)
        if os.path.exists(default_file_path):
            with open(default_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = '未找到转写结果文件'
    else:
        content = '未找到转写结果文件'
    
    # 查找原始音视频文件（用于预览）
    source_file = None
    upload_dir = os.path.join(app.root_path, UPLOAD_FOLDER)
    if os.path.exists(upload_dir):
        candidates = [
            f for f in os.listdir(upload_dir)
            if is_allowed_file(f) and os.path.splitext(f)[0] == base_name
        ]
        candidates.sort()
        if candidates:
            source_file = candidates[0]

    return render_template(
        'detail.html',
        filename=filename,
        files=files,
        content=content,
        default_file=default_file,
        source_file=source_file,
    )

@app.route('/view_file/<path:filename>')
def view_file(filename):
    # 分离文件夹名和文件名
    parts = filename.split('/')
    folder_name = parts[0]
    file_name = parts[1] if len(parts) > 1 else parts[0]
    file_path = os.path.join(app.root_path, OUTPUT_FOLDER, folder_name, file_name)
    
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return '文件不存在'

@app.route('/download_file/<path:filename>')
def download_file(filename):
    # 分离文件夹名和文件名
    parts = filename.split('/')
    folder_name = parts[0]
    file_name = parts[1] if len(parts) > 1 else parts[0]
    file_path = os.path.join(app.root_path, OUTPUT_FOLDER, folder_name, file_name)
    
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return '文件不存在'

@app.route('/source_file/<path:filename>')
def source_file(filename):
    upload_root = os.path.join(app.root_path, UPLOAD_FOLDER)
    target_path = os.path.abspath(os.path.normpath(os.path.join(upload_root, filename)))
    upload_root_abs = os.path.abspath(upload_root)
    if os.path.commonpath([upload_root_abs, target_path]) != upload_root_abs:
        return '非法路径'
    if not os.path.exists(target_path):
        return '文件不存在'
    return send_file(target_path, conditional=True)


@app.route('/save_output_file/<folder>/<path:filename>', methods=['POST'])
def save_output_file(folder, filename):
    data = request.get_json(silent=True) or {}
    content = data.get('content')
    if content is None:
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': '内容不能为空'})

    output_root = os.path.join(app.root_path, OUTPUT_FOLDER)
    target_path = os.path.abspath(os.path.normpath(os.path.join(output_root, folder, filename)))
    output_root_abs = os.path.abspath(output_root)
    if os.path.commonpath([output_root_abs, target_path]) != output_root_abs:
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': '非法路径'})

    if not os.path.exists(target_path):
        return jsonify({'status': 'error', 'code': Codes.INPUT_NOT_FOUND, 'message': '文件不存在'})

    try:
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"保存文件成功: {target_path}")
        return jsonify({'status': 'success', 'code': Codes.SUCCESS})
    except Exception as e:
        logger.error(format_message(Codes.FILE_IO, '保存文件失败', str(e)))
        return jsonify({'status': 'error', 'code': Codes.FILE_IO, 'message': str(e)})

@app.route('/delete_all_file/<path:filename>', methods=['POST'])
def delete_all_file(filename):
    import shutil
    
    # 删除源文件
    source_file = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
    if os.path.exists(source_file):
        try:
            os.remove(source_file)
            logger.info(f"源文件删除成功: {source_file}")
        except Exception as e:
            logger.error(format_message(Codes.FILE_IO, '删除源文件时出错', str(e)))
            return jsonify({'status': 'error', 'code': Codes.FILE_IO, 'message': f'删除源文件时出错: {str(e)}'})
    
    # 删除输出文件夹
    output_folder = os.path.join(app.root_path, OUTPUT_FOLDER, os.path.splitext(filename)[0])
    if os.path.exists(output_folder):
        try:
            shutil.rmtree(output_folder)
            logger.info(f"输出文件夹删除成功: {output_folder}")
        except Exception as e:
            logger.error(format_message(Codes.FILE_IO, '删除输出文件夹时出错', str(e)))
            return jsonify({'status': 'error', 'code': Codes.FILE_IO, 'message': f'删除输出文件夹时出错: {str(e)}'})
    
    # 删除转写记录
    records = load_transcription_records()
    records['records'] = [r for r in records['records'] if r['file_name'] != filename]
    save_transcription_records(records)
    
    return jsonify({'status': 'success', 'code': Codes.SUCCESS, 'message': '文件删除成功'})

@app.route('/delete_file_in_output/<folder>/<filename>', methods=['POST'])
def delete_file_in_output(folder, filename):
    # 构建文件路径
    file_path = os.path.join(app.root_path, OUTPUT_FOLDER, folder, filename)
    logger.info(f"尝试删除文件: {file_path}")
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"文件删除成功: {file_path}")
            return jsonify({'status': 'success', 'code': Codes.SUCCESS, 'message': '文件删除成功'})
        except Exception as e:
            logger.error(format_message(Codes.FILE_IO, '删除文件时出错', str(e)))
            return jsonify({'status': 'error', 'code': Codes.FILE_IO, 'message': f'删除文件时出错: {str(e)}'})
    
    return jsonify({'status': 'error', 'code': Codes.INPUT_NOT_FOUND, 'message': '文件不存在'})


def load_transcription_records():
    records_file = os.path.join(app.root_path, 'data/transcription_records.json')
    if os.path.exists(records_file):
        try:
            with open(records_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get('records', []), list):
                    return data
                logger.warning('转写记录格式异常，将重置记录')
        except Exception as e:
            logger.warning(f'读取转写记录失败，将重置记录: {e}')
    return {"records": []}

def save_transcription_records(records):
    records_file = os.path.join(app.root_path, 'data/transcription_records.json')
    os.makedirs(os.path.dirname(records_file), exist_ok=True)
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def update_transcription_record(filename, transcribed=False, last_time=None, created_time=None):
    if not isinstance(filename, str) or not filename.strip():
        logger.error(format_message(Codes.INVALID_ARGS, '转写记录文件名无效', str(filename)))
        return
    records = load_transcription_records()
    
    # 查找现有记录或创建新记录
    record = next((r for r in records['records'] if r['file_name'] == filename), None)
    if record is None:
        record = {
            'file_name': filename,
            'transcribed': False,
            'last_transcription_time': None,
            'created_time': created_time or time.strftime('%Y-%m-%d %H:%M:%S')
        }
        records['records'].append(record)
    
    # 更新记录
    record['transcribed'] = transcribed
    record['last_transcription_time'] = last_time
    
    save_transcription_records(records)


def transcribe_task(filename, steps='12', model_type=None, model_size=None):
    input_file = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
    file_output_dir = os.path.join(app.root_path, OUTPUT_FOLDER, os.path.splitext(filename)[0])
    os.makedirs(file_output_dir, exist_ok=True)
    
    update_transcription_record(filename)
    logger.info(f"开始任务: {filename} steps={steps} model_type={model_type or 'default'} model_size={model_size or 'default'}")
    socketio.emit('transcribe_progress', {'data': f'开始转写：{filename} (步骤：{steps})'})
    
    python_exec = sys.executable or 'python'
    cmd = [
        python_exec,
        '-u',
        str(ROOT_DIR / 'cli.py'),
        '-i', input_file,
        '-o', file_output_dir,
        '--steps', steps,
        '--prompts-dir', str(WEB_DIR / 'data' / 'prompts'),
        '--nobanner'
    ]
    if model_type:
        cmd.extend(['--transcribe-model-type', model_type])
    if model_size:
        cmd.extend(['--transcribe-model-size', model_size])
    
    try:
        if IS_WINDOWS:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            if process.stdout:
                for line in process.stdout:
                    line = clean_output_line(line)
                    if not should_skip_output(line):
                        socketio.emit('transcribe_progress', {'data': line})
            return_code = process.wait()
        else:
            import pty
            master_fd, slave_fd = pty.openpty()
            process = subprocess.Popen(
                cmd,
                stdout=slave_fd,
                stderr=slave_fd,
                text=True,
                bufsize=1
            )
            os.close(slave_fd)  # 关闭子进程中不再需要的文件描述符
            
            # 实时读取输出
            while True:
                try:
                    output = os.read(master_fd, 1024).decode()
                except OSError:
                    break
                if output:
                    # 将输出按行拆分并逐行发送
                    for line in output.splitlines():
                        line = clean_output_line(line)
                        if not should_skip_output(line):
                            socketio.emit('transcribe_progress', {'data': line})
                if process.poll() is not None:
                    break
            
            return_code = process.wait()
        if return_code == 0:
            update_transcription_record(filename, True, time.strftime('%Y-%m-%d %H:%M:%S'))
            socketio.emit('transcribe_complete', {'filename': filename})
            logger.info(f"任务完成: {filename}")
        else:
            socketio.emit('transcribe_progress', {'data': f'转写失败，返回码: {return_code}'})
            logger.error(format_message(Codes.TASK_FAIL, '转写失败', f'file={filename} code={return_code}'))
    except Exception as e:
        socketio.emit('transcribe_progress', {'data': f'转写出错: {str(e)}'})
        logger.error(format_message(Codes.TASK_FAIL, '转写出错', f'file={filename} err={e}'))
    finally:
        if not IS_WINDOWS:
            try:
                os.close(master_fd)
            except Exception:
                pass

# Prompt管理相关路由
@app.route('/list_prompts')
def list_prompts():
    prompts_dir = os.path.join(app.root_path, 'data', 'prompts')
    os.makedirs(prompts_dir, exist_ok=True)
    prompts = [f for f in os.listdir(prompts_dir) if f.endswith('.txt')]
    return jsonify({'prompts': prompts})

@app.route('/view_prompt/<filename>')
def view_prompt(filename):
    prompts_dir = os.path.join(app.root_path, 'data', 'prompts')
    file_path = os.path.join(prompts_dir, filename)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return '文件不存在'

@app.route('/save_prompt', methods=['POST'])
def save_prompt():
    data = request.get_json()
    filename = data.get('filename')
    content = data.get('content')
    
    if not filename or not content:
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': '文件名和内容不能为空'})
    
    if not filename.endswith('.txt'):
        return jsonify({'status': 'error', 'code': Codes.INVALID_ARGS, 'message': '文件必须以.txt结尾'})
    
    prompts_dir = os.path.join(app.root_path, 'data', 'prompts')
    os.makedirs(prompts_dir, exist_ok=True)
    file_path = os.path.join(prompts_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'success', 'code': Codes.SUCCESS})
    except Exception as e:
        return jsonify({'status': 'error', 'code': Codes.FILE_IO, 'message': str(e)})

@app.route('/delete_prompt/<filename>', methods=['POST'])
def delete_prompt(filename):
    prompts_dir = os.path.join(app.root_path, 'data', 'prompts')
    file_path = os.path.join(prompts_dir, filename)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({'status': 'success', 'code': Codes.SUCCESS})
        except Exception as e:
            return jsonify({'status': 'error', 'code': Codes.FILE_IO, 'message': str(e)})
    return jsonify({'status': 'error', 'code': Codes.INPUT_NOT_FOUND, 'message': '文件不存在'})

import logging
from logging.handlers import RotatingFileHandler

if __name__ == '__main__':
    # 配置日志
    # log_handler = RotatingFileHandler('app.log', maxBytes=1000000, backupCount=3)
    # log_handler.setFormatter(logging.Formatter(
    #     '%(asctime)s %(levelname)s: %(message)s '
    #     '[in %(pathname)s:%(lineno)d]'
    # ))
    # app.logger.addHandler(log_handler)
    app.logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    # 根据环境变量判断运行模式
    if os.getenv('FLASK_ENV') == 'production':
        secret = os.getenv('SECRET_KEY')
        if secret:
            app.config['SECRET_KEY'] = secret
        else:
            app.logger.warning('生产环境未设置 SECRET_KEY')
        socketio.run(app,allow_unsafe_werkzeug=True,debug=False, host='0.0.0.0', port=15000)
    else:
        socketio.run(app, debug=True, host='127.0.0.1', port=15000)
