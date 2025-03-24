import asyncio,requests
import logging
import re


from bilibili_api import video,user,sync
from bilibili_api import Credential,HEADERS
import httpx
import os
from urllib.parse import urlparse, parse_qs

#logging.basicConfig(level=logging.DEBUG)


# credential = Credential(
#     sessdata="x",
#     bili_jct="d",
#     buvid3="d",
#     dedeuserid="d",
#     ac_time_value="d"
# )

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

# def download_file_old(url, save_path, file_name):
#     os.makedirs(save_path, exist_ok=True)
#     file_path = os.path.join(save_path, file_name)
#     response = requests.get(url,headers=HEADERS)

#     if response.status_code == 200:
#         with open(file_path, 'wb') as file:
#             file.write(response.content)
#         print(f'文件已成功下载到 {file_path}')
#         return True
#     else:
#         print(f'下载失败，状态码: {response.status_code}')
#         return False

# async def download_audio_old(bvid,save_path):

#     v = video.Video(bvid=bvid)
#     info = await v.get_info()

#     download_info = await v.get_download_url(page_index=0)
#     audio_info = download_info['dash']['audio'] # list

#     # 文件名：【作者】标题.mp4
#     title = info['title']
#     owner = info['owner']['name']
#     filename = f"【{owner}】{title}.mp4"

#     audio_urls = []
#     for each in audio_info:
#         try:
#             audio_urls.append(each['base_url'])
#             try:
#                 for url in each['backup_url']:
#                     audio_urls.append(url)
#             except: pass
#         except: pass

#     download_flag = False
#     for url in audio_urls:
#         try:
#             if download_file_old(url, save_path, filename):
#                 download_flag = True
#                 logging.info(f"{filename} 下载完成。")
#                 break
#         except:
#             logging.DEBUG("这个url不行，换一个")

#     if download_flag:
#         return True
#     return False

async def download_url(url: str, save_path: str,file_name: str):
    '''

    :param url: 下载链接
    :param save_path: 保存的文件夹
    :param file_name: 保存的文件名
    :return: 下载是否成功
    '''
    os.makedirs(save_path, exist_ok=True)
    file_path = os.path.join(save_path, file_name)

    try:
        async with httpx.AsyncClient(headers=HEADERS) as sess:
            resp = await sess.get(url)
            length = resp.headers.get('content-length')
            with open(file_path, 'wb') as f:
                process = 0
                for chunk in resp.iter_bytes(1024):
                    if not chunk:
                        break
                    process += len(chunk)
                    # print(f'下载 {process} / {length}')
                    f.write(chunk)
        logging.info(f"下载{file_name}完成。")
        return True
    except Exception as e:
        logging.debug(e)
        logging.info(f"下载 {file_name} 不成功。")
        return False

def download_audio(bvid,page,save_path):
    '''
    下载某个视频的音频
    :param bvid: bv号
    :param page: 视频分p序号，如果为None则默认为0
    :param save_path: 保存到哪里
    :return: 是否成功
    '''
    v = video.Video(bvid=bvid,)
    info = sync(v.get_info())

    # 获取视频下载链接
    page_index = page - 1 if page is not None else 0
    download_url_data = sync(v.get_download_url(page_index=page_index))
    # 解析视频下载信息
    detecter = video.VideoDownloadURLDataDetecter(data=download_url_data)
    streams = detecter.detect_best_streams()

    # 文件名：【作者】标题.mp4
    title = info['title']
    owner = info['owner']['name']
    filename = f"[{owner}]{title}.mp4"
    filename = clean_filename(filename)
    logging.debug(f"文件名：{filename}")

    return sync(download_url(streams[1].url,save_path,filename))

# def download_all_pages_audio(bvid,save_path):
#     v = video.Video(bvid=bvid)
#     info = sync(v.get_info())

#     pages = sync(v.get_pages())
#     for page in pages:
#         cid = page['cid']
#         page_num = page['page']
#         page_name = page['part']

#         download_url_data = sync(v.get_download_url(cid=cid))
#         # 解析视频下载信息
#         detecter = video.VideoDownloadURLDataDetecter(data=download_url_data)

#         streams = detecter.detect_best_streams()
#         # 文件名：【作者】_【标题】_【p021】_【分p名称】.mp4
#         title = info['title']
#         owner = info['owner']['name']
#         filename = f"[{owner}]_[{title}]_[p{str(page_num).zfill(3)}].mp4"
#         logging.debug(f"文件名：{filename}")

#         sync(download_url(streams[1].url, save_path, filename))

#     return True



async def parse_bilibili_url(url: str) -> tuple[str, int | None]:
    '''
    从B站URL中提取BVID和page数
    :param url: B站视频URL，支持长链接和短链接(b23.tv)
    :return: (bvid, page_number)，如果没有指定page，则返回None
    '''
    # 处理短链接
    if 'b23.tv' in url:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            url = str(response.url)

    # 提取BVID
    bv_match = re.search(r'BV[\w]+', url)
    if not bv_match:
        raise ValueError('无法从URL中提取BVID')
    bvid = bv_match.group(0)

    # 提取page数
    parsed_url = urlparse(url)
    print(parsed_url)
    query_params = parse_qs(parsed_url.query)
    print(query_params)
    page = query_params.get('p', [None])[0]
    page = int(page) if page is not None else None
    print("page = ", page)

    return bvid, page

def download_from_url(url: str, save_path: str) -> bool:
    '''
    通过B站视频URL直接下载视频
    :param url: B站视频URL，支持长链接和短链接(b23.tv)
    :param save_path: 保存路径
    :return: 是否下载成功
    '''
    try:
        bvid, page = sync(parse_bilibili_url(url))
        logging.info(f"解析结果：BVID={bvid}, Page={page}")
        return download_audio(bvid, page, save_path)
    except Exception as e:
        logging.error(f"下载失败：{e}")
        return False

if __name__ == '__main__':
    ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
    save_path = os.path.join(ROOT_PATH,"bilibili_download")

    # 测试长链接
    url = "https://www.bilibili.com/video/BV1Yx4y1n73F?spm_id_from=333.788.videopod.episodes&vd_source=3bdba0dc315ccb3cc89fb247d4a9a72c&p=5"
    bvid, page = sync(parse_bilibili_url(url))
    print(f"长链接解析结果：BVID={bvid}, Page={page}")

    # 测试短链接
    url = "https://b23.tv/JZQWAkY"
    bvid, page = sync(parse_bilibili_url(url))
    print(f"短链接解析结果：BVID={bvid}, Page={page}")

    download_from_url("https://b23.tv/JZQWAkY","bilbili_download")