from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import os
import time
import pty
import logging
import subprocess
from threading import Thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# 配置文件存储路径
UPLOAD_FOLDER = 'data/upload'
OUTPUT_FOLDER = 'data/output'

# 确保目录存在
os.makedirs(os.path.join(app.root_path, UPLOAD_FOLDER), exist_ok=True)
os.makedirs(os.path.join(app.root_path, OUTPUT_FOLDER), exist_ok=True)

@app.route('/')
def index():
    # 获取上传文件列表
    files = os.listdir(os.path.join(app.root_path, UPLOAD_FOLDER))
    
    # 获取转写记录
    records = load_transcription_records()
    file_records = {record['file_name']: record for record in records['records']}
    
    # 为每个文件准备转写信息
    files_info = []
    for file in files:
        record = file_records.get(file, {'transcribed': False, 'last_transcription_time': None})
        files_info.append({
            'name': file,
            'transcribed': record['transcribed'],
            'last_time': record['last_transcription_time'] or '未转写'
        })
    
    return render_template('index.html', files=files_info)

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'URL不能为空'})
    
    from crawler import download_video as dl
    upload_dir = os.path.join(app.root_path, UPLOAD_FOLDER)
    filename = dl(url, upload_dir)
    
    if filename:
        return jsonify({'status': 'success', 'message': f'视频 {filename} 下载成功'})
    else:
        return jsonify({'status': 'error', 'message': '下载失败'})

@app.route('/transcribe', methods=['POST'])
def start_transcribe():
    filename = request.form.get('filename')
    steps = request.form.get('steps', '12')  # 默认只执行转写步骤

    print("steps:", steps)
    if not filename:
        return jsonify({'status': 'error', 'message': '未提供文件名'})
    
    # 启动转写任务
    thread = Thread(target=transcribe_task, args=(filename, steps))
    thread.start()
    return jsonify({'status': 'success'})

@app.route('/transcribe/<filename>')
def view_transcription(filename):
    # 获取输出目录路径
    file_output_dir = os.path.join(app.root_path, OUTPUT_FOLDER, os.path.splitext(filename)[0])
    
    # 获取目录下的所有文件
    files = []
    if os.path.exists(file_output_dir):
        files = [{'name': f} for f in os.listdir(file_output_dir)]
    
    # 获取默认显示的文件内容（音频转写文件）
    default_file = f'{os.path.splitext(filename)[0]}_音频_转写.txt'
    content = ''
    default_file_path = os.path.join(file_output_dir, default_file)
    if os.path.exists(default_file_path):
        with open(default_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    else:
        content = '未找到转写结果文件'
    
    return render_template('detail.html', filename=filename, files=files, content=content)

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

@app.route('/delete_file/<path:filename>', methods=['POST'])
def delete_file(filename):
    # 分离文件夹名和文件名
    parts = filename.split('/')
    folder_name = parts[0]
    file_name = parts[1] if len(parts) > 1 else parts[0]
    file_path = os.path.join(app.root_path, OUTPUT_FOLDER, folder_name, file_name)
    
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'status': 'success'})
    return jsonify({'status': 'error', 'message': '文件不存在'})

import json
import sys
sys.path.append('..')
from src.transcription import transcribe_audio

def load_transcription_records():
    records_file = os.path.join(app.root_path, 'data/transcription_records.json')
    if os.path.exists(records_file):
        with open(records_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"records": []}

def save_transcription_records(records):
    records_file = os.path.join(app.root_path, 'data/transcription_records.json')
    with open(records_file, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

def update_transcription_record(filename, transcribed=False, last_time=None):
    records = load_transcription_records()
    
    # 查找现有记录或创建新记录
    record = next((r for r in records['records'] if r['file_name'] == filename), None)
    if record is None:
        record = {
            'file_name': filename,
            'transcribed': False,
            'last_transcription_time': None
        }
        records['records'].append(record)
    
    # 更新记录
    record['transcribed'] = transcribed
    record['last_transcription_time'] = last_time
    
    save_transcription_records(records)

# def transcribe_task(filename, steps='12'):
#     input_file = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
#     # 为每个文件创建独立的输出文件夹
#     file_output_dir = os.path.join(app.root_path, OUTPUT_FOLDER, os.path.splitext(filename)[0])
#     os.makedirs(file_output_dir, exist_ok=True)
    
#     # 更新转写状态
#     update_transcription_record(filename)
    
#     try:
#         # 构建cli.py命令
#         cmd = [
#             'python3','-u', # 无缓冲模式！
#             os.path.join(os.path.dirname(app.root_path), 'cli.py'),
#             '-i', input_file,
#             '-o', file_output_dir,
#             '--steps', steps,  # 执行指定步骤
#             '--prompts-dir', os.path.join(os.path.dirname(app.root_path),'web','data', 'prompts'),  # 指定prompts目录
#             '--nobanner'
#         ]
        
#         # 使用Popen执行命令并实时获取输出
#         process = subprocess.Popen(
#             cmd,
#             stdout=subprocess.PIPE,
#             stderr=subprocess.PIPE,
#             universal_newlines=True,
#             bufsize=1
#         )
        
#         # 实时读取stdout和stderr并通过socketio发送
#         while True:
#             # 读取stdout
#             sys.stdout.flush()
#             output = process.stdout.readline()
#             if output:
#                 print(output.strip())
#                 socketio.emit('transcribe_progress', {'data': output.strip()})
            
#             # 读取stderr
#             error = process.stderr.readline()
#             if error:
#                 print(error.strip())
#                 socketio.emit('transcribe_progress', {'data': error.strip()})
            
#             # 检查进程是否结束
#             if output == '' and error == '' and process.poll() is not None:
#                 break
        
#         # 检查命令执行结果
#         return_code = process.wait()
#         if return_code == 0:
#             # 更新转写记录
#             update_transcription_record(filename, True, time.strftime('%Y-%m-%d %H:%M:%S'))
#             # 发送完成消息
#             socketio.emit('transcribe_complete', {'filename': filename})
#         else:
#             error = process.stderr.read()
#             socketio.emit('transcribe_progress', {'data': f'转写失败: {error}'})
#     except Exception as e:
#         socketio.emit('transcribe_progress', {'data': f'转写出错: {str(e)}'})



def transcribe_task(filename, steps='12'):
    input_file = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
    file_output_dir = os.path.join(app.root_path, OUTPUT_FOLDER, os.path.splitext(filename)[0])
    os.makedirs(file_output_dir, exist_ok=True)
    
    update_transcription_record(filename)
    
    cmd = [
        'python3',  # 如果 cli.py 是 Python 脚本，仍然可以保留 -u 参数
        '-u',
        os.path.join(os.path.dirname(app.root_path), 'cli.py'),
        '-i', input_file,
        '-o', file_output_dir,
        '--steps', steps,
        '--prompts-dir', os.path.join(os.path.dirname(app.root_path),'web','data', 'prompts'),
        '--nobanner'
    ]
    
    try:
        # 创建伪终端
        master_fd, slave_fd = pty.openpty()
        
        process = subprocess.Popen(
            cmd,
            stdout=slave_fd,
            stderr=slave_fd,
            universal_newlines=True,
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
                    print(line)
                    socketio.emit('transcribe_progress', {'data': line})
            if process.poll() is not None:
                break
        
        return_code = process.wait()
        if return_code == 0:
            update_transcription_record(filename, True, time.strftime('%Y-%m-%d %H:%M:%S'))
            socketio.emit('transcribe_complete', {'filename': filename})
        else:
            error = process.stderr.read()
            socketio.emit('transcribe_progress', {'data': f'转写失败: {error}'})
    except Exception as e:
        socketio.emit('transcribe_progress', {'data': f'转写出错: {str(e)}'})

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
        return jsonify({'status': 'error', 'message': '文件名和内容不能为空'})
    
    if not filename.endswith('.txt'):
        return jsonify({'status': 'error', 'message': '文件必须以.txt结尾'})
    
    prompts_dir = os.path.join(app.root_path, 'data', 'prompts')
    os.makedirs(prompts_dir, exist_ok=True)
    file_path = os.path.join(prompts_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/delete_prompt/<filename>', methods=['POST'])
def delete_prompt(filename):
    prompts_dir = os.path.join(app.root_path, 'data', 'prompts')
    file_path = os.path.join(prompts_dir, filename)
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    return jsonify({'status': 'error', 'message': '文件不存在'})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=15000)