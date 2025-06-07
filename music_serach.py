"""
网易云音乐歌单信息抓取与可视化工具
功能特性：
1. 自动获取完整歌单数据（支持超大歌单）
2. 生成三种格式的输出：TXT文本、Markdown文档、信息图
3. 智能封面下载与拼接（自动处理无效封面）
4. 完善的错误处理与重试机制
5. 可定制的样式配置
"""

import requests
import json
import os
import re
from typing import List, Dict, Optional
from PIL import Image, ImageDraw, ImageFont
from math import sqrt
import time


# -------------------- 全局配置 --------------------
class Config:
    # 样式配置
    STYLE = {
        'font_path': 'msyh.ttc',  # 字体文件路径
        'cover_size': (300, 300),  # 封面下载尺寸
        'tile_size': (200, 200),  # 拼接时的封面尺寸
        'max_filename_length': 50,  # 保存文件名最大长度
        'max_retries': 3,  # 网络请求重试次数
        'retry_delay': 1,  # 重试延迟(秒)

        # 信息图样式
        'image_style': {
            'bg_color': (245, 245, 245),  # 背景颜色
            'title_color': (0, 102, 204),  # 标题颜色
            'text_color': (51, 51, 51),  # 正文颜色
            'line_color': (200, 200, 200),  # 装饰线颜色
            'margin': 50,  # 页面边距
            'line_spacing': 10,  # 行间距
            'title_font_size': 28,  # 标题字体大小
            'text_font_size': 20,  # 正文字体大小
        }
    }

    # 网络配置
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://music.163.com/',
        'Cookie':  'appver=1.5.2;os=pc;' + 'NMTID=00OXJx62w9eOjoK-Ev5sF0TywjN1l4AAAGWKIOKAg; _iuqxldmzr_=32; _ntes_nnid=20a51421dd4436d81f1fc277f7ff266c,1744436430782; _ntes_nuid=20a51421dd4436d81f1fc277f7ff266c; WEVNSM=1.0.0; WNMCID=ohdpwm.1744436431025.01.0; WM_NI=0F2tyGEBC6PXRWfb9Z9sheRjV%2BUkknkH2DgxJlhayPmOfQO6GGIyTnsghHDSH6CtiIq8vFPsdawb%2FrUvq2MXqf50mIO%2F%2BLYRYgpAHXKWaHPMkWGNhpkGCi0bqoZB4CNlelU%3D; WM_NIKE=9ca17ae2e6ffcda170e2e6eeb0cf3ba3a9bbb6ce6aadb88bb7d84e828b9b87c26b96b38ad1d5218892008dec2af0fea7c3b92af49afe95fc4d879e8dd7d3549289aa83bc52fbada886d16296f59b8cea66a998fea5e6748ab4a882fc5caf91aab2ce3e8599879ad766b1b9a8a9c7598cea8d95ec43b3e8baa7d379a8bfb983ae7a97aabfd3d054b3bafbd1f0438df1e5addc5a9bb9c0a2cb548989afa9d347a98989afeb7ca9998d8ab36ab3b196a3b7498eb4ab8dd837e2a3; WM_TID=4Dcf%2BwZ61MNEBQQBURaTORnRhA7Xdh1y; sDeviceId=YD-rLHNWvwLuL1BElBUVAKSfAmRhF%2BDN6cY; __snaker__id=u0tSsTmPQNaP3NDg; ntes_utid=tid._.cjbcVZny9JhBA1EVABPWfBnV1FqSIqZM._.0; gdxidpyhxdE=mBc%5CQj%2FIYjrXInzcRYDxfasZSEu1PxubuP9rx52OlEQ%2F0M49r8q4cb85wKLQ797r9MWu84CTdj%2FkLwCnJEf7JzmULc9N%2FrxYM4c08x0juxX2sM%5CKSmrj%2BkHu7cIxWBD%5CW88PMsOyhraHO518EKtzOjDgy0CBZiaBLAMgMm3B4wI%5C7HMY%3A1744437406702; __csrf=cad5908cda66bcd8b84aeecdb3cfc83a; ntes_kaola_ad=1; os=pc; JSESSIONID-WYYY=sex4aUiVUtlZz3IpuKlOslXRXpWAOyZ0UTxmtiK8pwT9Qt2E2%2FdvZQDIVzJ1U5cZJOFSZx8VKylp23NPoejQtSDYy3TedQQi0OQ2hTiHKaTndpZ7PBn18E4PXjxKDlSZhbXH6hK%2FTB8bKGtQeaGITt3BihWtyRaH5jb2yy6RQnqmz9%2B7%3A1744443452847',
    }


# -------------------- 工具函数 --------------------
def safe_filename(filename: str) -> str:
    """生成安全文件名：移除非法字符并限制长度"""
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if len(filename) > Config.STYLE['max_filename_length']:
        filename = filename[:Config.STYLE['max_filename_length']]
    return filename.strip()


def retry_request(url: str, **kwargs) -> requests.Response:
    """带重试机制的请求函数"""
    for _ in range(Config.STYLE['max_retries']):
        try:
            response = requests.get(url, **kwargs)
            if response.status_code == 200:
                return response
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(Config.STYLE['retry_delay'])
    raise Exception(f"请求失败: {url}")


# -------------------- 核心功能 --------------------
def fetch_playlist_data(playlist_id: str) -> Dict:
    """
    获取完整歌单数据
    :param playlist_id: 歌单ID
    :return: 包含歌单数据的字典
    """
    api_url = f"https://music.163.com/api/v6/playlist/detail?id={playlist_id}&n=1000"
    try:
        response = retry_request(api_url, headers=Config.HEADERS)
        data = json.loads(response.text)
        if data.get('code') != 200:
            raise ValueError(f"API返回错误: {data.get('message')}")
        return data
    except json.JSONDecodeError:
        raise ValueError("API返回数据解析失败")


def generate_text_files(tracks: List[Dict], playlist_info: Dict) -> None:
    """
    生成文本格式文件（TXT和Markdown）
    :param tracks: 歌曲列表
    :param playlist_info: 歌单元数据
    """
    # TXT文件
    with open('playlist_info.txt', 'w', encoding='utf-8') as f:
        f.write(f"歌单名称: {playlist_info['name']}\n")
        f.write(f"创建者: {playlist_info['creator']['nickname']}\n")
        f.write(f"歌曲数量: {playlist_info['trackCount']}\n\n")

        for idx, track in enumerate(tracks, 1):
            song_name = track['name']
            artists = ', '.join(ar['name'] for ar in track['ar'])
            album = track['al']['name']
            f.write(f"{idx}. {song_name}\n   歌手: {artists}\n   专辑: {album}\n\n")

    # Markdown文件
    with open('playlist_info.md', 'w', encoding='utf-8') as f:
        f.write(f"# {playlist_info['name']}\n\n")
        f.write(f"- 创建者: {playlist_info['creator']['nickname']}\n")
        f.write(f"- 歌曲数量: {playlist_info['trackCount']}\n")
        f.write(f"- 播放次数: {playlist_info['playCount']}\n\n")
        f.write("## 歌曲列表\n\n")

        for idx, track in enumerate(tracks, 1):
            song_name = track['name']
            artists = ' / '.join(ar['name'] for ar in track['ar'])
            album = track['al']['name']
            f.write(f"{idx}. **{song_name}** - {artists}  \n   *{album}*\n\n")


def download_covers(tracks: List[Dict]) -> List[str]:
    """
    下载所有歌曲封面
    :return: 成功下载的封面路径列表
    """
    os.makedirs('covers', exist_ok=True)
    downloaded = []

    for track in tracks:
        try:
            cover_url = track['al']['picUrl'].replace(
                '?param=90y90',
                f"?param={Config.STYLE['cover_size'][0]}y{Config.STYLE['cover_size'][1]}"
            )
            song_name = safe_filename(track['name'])
            filepath = f"covers/{song_name}.jpg"

            if not os.path.exists(filepath):
                response = retry_request(cover_url)
                with open(filepath, 'wb') as f:
                    f.write(response.content)
            downloaded.append(filepath)
        except Exception as e:
            print(f"封面下载失败: {track['name']} - {str(e)}")

    return downloaded


def generate_cover_collage(image_paths: List[str]) -> Optional[str]:
    """
    生成封面拼贴图
    :param image_paths: 封面图片路径列表
    :return: 生成图片的路径（失败返回None）
    """
    if not image_paths:
        return None

    try:
        # 动态计算布局
        img_count = len(image_paths)
        cols = int(sqrt(img_count))
        rows = (img_count + cols - 1) // cols  # 向上取整

        # 加载并调整图片尺寸
        images = []
        for path in image_paths:
            with Image.open(path) as img:
                img = img.resize(Config.STYLE['tile_size'])
                images.append(img)

        # 创建画布
        canvas_width = Config.STYLE['tile_size'][0] * cols
        canvas_height = Config.STYLE['tile_size'][1] * rows
        canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))

        # 拼接图片
        for i, img in enumerate(images):
            x = (i % cols) * Config.STYLE['tile_size'][0]
            y = (i // cols) * Config.STYLE['tile_size'][1]
            canvas.paste(img, (x, y))

        output_path = 'cover_collage.jpg'
        canvas.save(output_path)
        return output_path
    except Exception as e:
        print(f"封面拼接失败: {str(e)}")
        return None


def generate_info_image(tracks: List[Dict], playlist_info: Dict) -> Optional[str]:
    """
    生成美观的信息图
    :return: 生成图片的路径（失败返回None）
    """
    try:
        style = Config.STYLE['image_style']
        font_title = ImageFont.truetype(Config.STYLE['font_path'], style['title_font_size'])
        font_text = ImageFont.truetype(Config.STYLE['font_path'], style['text_font_size'])

        # 计算画布尺寸
        line_height = style['text_font_size'] + style['line_spacing']
        y_offset = style['margin'] * 2 + style['title_font_size']

        # 预计算总高度
        total_height = y_offset
        for _ in tracks:
            total_height += 3 * line_height + style['line_spacing'] * 2

        # 创建画布
        img = Image.new('RGB', (800, total_height + 50), style['bg_color'])
        draw = ImageDraw.Draw(img)

        # 绘制标题
        title = f"{playlist_info['name']} - 共{len(tracks)}首"
        draw.text(
            (style['margin'], style['margin']),
            title,
            fill=style['title_color'],
            font=font_title
        )

        # 绘制歌曲列表
        y = y_offset
        for idx, track in enumerate(tracks, 1):
            text = [
                f"{idx}. {track['name']}",
                f"   歌手: {', '.join(ar['name'] for ar in track['ar'])}",
                f"   专辑: {track['al']['name']}"
            ]

            for line in text:
                draw.text(
                    (style['margin'], y),
                    line,
                    fill=style['text_color'],
                    font=font_text
                )
                y += line_height
            y += style['line_spacing']

        # 添加装饰线
        draw.line(
            (style['margin'] // 2, y + 10, 800 - style['margin'] // 2, y + 10),
            fill=style['line_color'],
            width=2
        )

        output_path = 'playlist_info.jpg'
        img.save(output_path)
        return output_path
    except Exception as e:
        print(f"信息图生成失败: {str(e)}")
        return None


def main(playlist_id: str) -> None:
    """主流程控制器"""
    try:
        # 获取数据
        data = fetch_playlist_data(playlist_id)
        playlist_info = data['playlist']
        tracks = playlist_info['tracks']
        print(f"成功获取 {len(tracks)} 首歌曲")

        # 生成文本文件
        generate_text_files(tracks, playlist_info)
        print("已生成 TXT 和 Markdown 文件")

        # 处理封面
        cover_paths = download_covers(tracks)
        if collage_path := generate_cover_collage(cover_paths):
            print(f"封面拼贴图已保存至: {collage_path}")

        # 生成信息图
        if info_image_path := generate_info_image(tracks, playlist_info):
            print(f"歌单信息图已保存至: {info_image_path}")

    except Exception as e:
        print(f"程序运行出错: {str(e)}")
        exit(1)


if __name__ == "__main__":
    PLAYLIST_ID = "2704863897"  # 替换为你的歌单ID
    main(PLAYLIST_ID)