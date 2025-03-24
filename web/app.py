from flask import Flask, render_template, request, jsonify, send_file
from flask_socketio import SocketIO, emit
import os
import time
import pty
import logging
import subprocess
from threading import Thread

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!?s3cReT1-df1ocn1oi3ofinsd'
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
        record = file_records.get(file, {'transcribed': False, 'last_transcription_time': None, 'created_time': None})
        if not record.get('created_time'):
            # 如果没有创建时间记录，则更新记录
            update_transcription_record(file, created_time=time.strftime('%Y-%m-%d %H:%M:%S'))
            record['created_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        
        files_info.append({
            'name': file,
            'transcribed': record['transcribed'],
            'last_time': record['last_transcription_time'] or '未转写',
            'created_time': record['created_time']
        })
    
    # 按创建时间倒序排序
    files_info.sort(key=lambda x: x['created_time'] or '', reverse=True)
    
    return render_template('index.html', files=files_info)

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'URL不能为空'})
    
    from crawler import download_media
    upload_dir = os.path.join(app.root_path, UPLOAD_FOLDER)
    try:
        filename = download_media(url, upload_dir)
        if filename:
            # 记录文件创建时间
            update_transcription_record(filename, created_time=time.strftime('%Y-%m-%d %H:%M:%S'))
            socketio.emit('download_progress', {'status': 'success', 'message': f'文件 {filename} 下载成功'})
            return jsonify({'status': 'success', 'message': f'文件 {filename} 下载成功'})
        else:
            socketio.emit('download_progress', {'status': 'error', 'message': '下载失败'})
            return jsonify({'status': 'error', 'message': '下载失败'})
    except Exception as e:
        error_message = str(e)
        socketio.emit('download_progress', {'status': 'error', 'message': error_message})
        return jsonify({'status': 'error', 'message': error_message})

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

@app.route('/delete_all_file/<path:filename>', methods=['POST'])
def delete_all_file(filename):
    import shutil
    
    # 删除源文件
    source_file = os.path.join(app.root_path, UPLOAD_FOLDER, filename)
    if os.path.exists(source_file):
        try:
            os.remove(source_file)
            print(f"[DEBUG] 源文件删除成功: {source_file}")
        except Exception as e:
            print(f"[DEBUG] 删除源文件时出错: {str(e)}")
            return jsonify({'status': 'error', 'message': f'删除源文件时出错: {str(e)}'})
    
    # 删除输出文件夹
    output_folder = os.path.join(app.root_path, OUTPUT_FOLDER, os.path.splitext(filename)[0])
    if os.path.exists(output_folder):
        try:
            shutil.rmtree(output_folder)
            print(f"[DEBUG] 输出文件夹删除成功: {output_folder}")
        except Exception as e:
            print(f"[DEBUG] 删除输出文件夹时出错: {str(e)}")
            return jsonify({'status': 'error', 'message': f'删除输出文件夹时出错: {str(e)}'})
    
    # 删除转写记录
    records = load_transcription_records()
    records['records'] = [r for r in records['records'] if r['file_name'] != filename]
    save_transcription_records(records)
    
    return jsonify({'status': 'success', 'message': '文件删除成功'})

@app.route('/delete_file_in_output/<folder>/<filename>', methods=['POST'])
def delete_file_in_output(folder, filename):
    # 构建文件路径
    file_path = os.path.join(app.root_path, OUTPUT_FOLDER, folder, filename)
    print(f"[DEBUG] 尝试删除文件: {file_path}")
    
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print(f"[DEBUG] 文件删除成功: {file_path}")
            return jsonify({'status': 'success', 'message': '文件删除成功'})
        except Exception as e:
            print(f"[DEBUG] 删除文件时出错: {str(e)}")
            return jsonify({'status': 'error', 'message': f'删除文件时出错: {str(e)}'})
    
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

def update_transcription_record(filename, transcribed=False, last_time=None, created_time=None):
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
    socketio.run(app, debug=True, host='0.0.0.0', port=15000)

    # 生产服务器
    #socketio.run(app,debug=False,host="192.168.111.2",port=15000)