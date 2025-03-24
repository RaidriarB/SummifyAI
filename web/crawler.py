import os
import yt_dlp

def download_video(url, output_dir):
    """
    下载视频到指定目录
    
    Args:
        url (str): 视频URL
        output_dir (str): 输出目录
    
    Returns:
        str: 下载后的文件名，如果下载失败则返回None
    """
    try:
        # 配置yt-dlp选项
        ydl_opts = {
            'format': 'best',  # 下载最佳质量
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        
        # 下载视频
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_title = info['title']
            video_ext = info['ext']
            return f"{video_title}.{video_ext}"
            
    except Exception as e:
        print(f"下载视频时出错: {e}")
        return None