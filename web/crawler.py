import os
import re
import yt_dlp
from spiders.bilibili import download_from_url as download_bilibili_from_url
from spiders.xiaoyuzhou import download_from_url as download_xiaoyuzhou_from_url


def is_valid_url(url):
    # 简单URL格式验证
    pattern = re.compile(r'https?://(?:www\.)?\S+\.[a-zA-Z]{2,}')
    return bool(pattern.match(url))


def get_platform(url):
    # 根据域名判断平台
    if 'bilibili.com' in url or 'b23.tv' in url:
        return 'bilibili'
    elif 'xiaoyuzhoufm.com' in url:
        return 'xiaoyuzhou'
    else:
        return None

def download_media(url, output_dir):
    # 检查URL合法性
    if not is_valid_url(url):
        print('无效的URL')
        return None

    # 判断平台
    platform = get_platform(url)

    # 调用相应平台的下载函数
    if platform == 'bilibili':
        return download_bilibili_from_url(url, output_dir)
    elif platform == 'xiaoyuzhou':
        return download_xiaoyuzhou_from_url(url, output_dir)
    else:
        print('不支持的平台')
        return None
