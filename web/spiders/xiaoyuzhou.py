import requests
from bs4 import BeautifulSoup
import json
import time
import random
import os
import re

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    ]
    return random.choice(user_agents)

def clean_filename(filename):
    """清理文件名，移除不合法字符"""
    # 移除或替换不合法字符
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    # 移除多余的空格和下划线
    filename = re.sub(r'\s+', '_', filename)
    filename = re.sub(r'_+', '_', filename)
    # 移除首尾的空格和下划线
    filename = filename.strip('_ ')
    return filename

def extract_next_data(html_content):
    """从HTML中提取__NEXT_DATA__脚本标签的内容和播客标题"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 提取标题
    meta_tags = soup.find_all("meta")
    title = None
    for meta in meta_tags:
        if meta.get("property") == "og:title":
            title = meta.get("content")
            break
    
    # 提取音频链接
    next_data = soup.find('script', {'id': '__NEXT_DATA__'})
    audio_url = None
    if next_data:
        try:
            data = json.loads(next_data.string)
            audio_url = data['props']['pageProps']['episode']['media']['source']['url']
        except (json.JSONDecodeError, KeyError) as e:
            print(f"解析JSON数据失败：{e}")
    
    return title, audio_url

def download_from_url(url, save_path):
    """下载小宇宙播客音频
    
    Args:
        url (str): 小宇宙播客链接
        save_path (str): 保存路径
        
    Returns:
        str | None: 下载成功返回文件名，失败返回 None
    """
    # 设置请求头
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.xiaoyuzhoufm.com/',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        # 获取音频下载链接和标题
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"请求失败，状态码：{response.status_code}")
            return None
            
        title, audio_url = extract_next_data(response.text)
        if not audio_url:
            print("未找到音频下载链接")
            return None
        
        if not title:
            print("未找到播客标题，使用URL作为文件名")
            title = url.split('/')[-1]
            
        # 创建保存目录
        os.makedirs(save_path, exist_ok=True)
        
        # 清理文件名并添加扩展名
        file_name = clean_filename(title) + '.mp3'
        file_path = os.path.join(save_path, file_name)
        
        # 下载音频文件
        print(f"开始下载音频文件到：{file_path}")
        audio_response = requests.get(audio_url, headers=headers, stream=True)
        if audio_response.status_code != 200:
            print(f"下载音频失败，状态码：{audio_response.status_code}")
            return None
            
        with open(file_path, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    
        print(f"音频文件下载完成：{file_path}")
        return file_name
        
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误：{e}")
        return None
    except Exception as e:
        print(f"下载过程发生错误：{e}")
        return None

if __name__ == '__main__':
    url = "https://www.xiaoyuzhoufm.com/episode/6495c2c9932f350aaee96480"
    save_path = "xyz"
    download_from_url(url, save_path)
