"""
网易云歌单分析系统 - Web版
使用说明：
1. 安装依赖：pip install flask requests Pillow
2. 获取DeepSeek API Key：https://platform.deepseek.com/
3. 运行程序：python app.py
"""

import os
import re
import json
import tempfile
from math import sqrt
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import requests

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# 配置参数
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_API_KEY = "sk-0e09bf355f1b4957a9c8ee4bc3b94113"  # 在此处替换你的API Key


class StyleConfig:
    """样式配置容器"""

    def __init__(self):
        self.cover_size = (300, 300)
        self.tile_size = (200, 200)
        self.font_path = "msyh.ttc"
        self.image_style = {
            'bg_color': (245, 245, 245),
            'title_color': (0, 102, 204),
            'text_color': (51, 51, 51),
            'margin': 50,
            'line_spacing': 10,
            'title_font_size': 28,
            'text_font_size': 20
        }


style_config = StyleConfig()


# -------------------- 工具函数 --------------------
def safe_filename(filename):
    """生成安全文件名"""
    return re.sub(r'[\\/*?:"<>|]', '', filename)[:50]


def analyze_with_deepseek(content, prompt):
    """调用DeepSeek API进行分析"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }

    payload = {
        "messages": [
            {"role": "system", "content": "你是一个专业的音乐评论家，擅长分析歌单风格和封面艺术"},
            {"role": "user", "content": f"{prompt}\n\n{content}"}
        ],
        "model": "deepseek-chat",
        "temperature": 0.7
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"分析失败: {str(e)}"


# -------------------- 核心功能 --------------------
def process_playlist(playlist_id, user_cookie):
    """处理歌单的全流程"""
    # 获取歌单数据
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Cookie': user_cookie,
        'Referer': 'https://music.163.com/'
    }

    api_url = f"https://music.163.com/api/v6/playlist/detail?id={playlist_id}&n=1000"
    response = requests.get(api_url, headers=headers)
    if response.status_code != 200:
        raise Exception("获取歌单数据失败")

    data = response.json()
    playlist_info = data['playlist']
    tracks = playlist_info['tracks']

    # 下载封面
    cover_paths = []
    for track in tracks:
        try:
            cover_url = track['al']['picUrl'].replace(
                '?param=90y90',
                f"?param={style_config.cover_size[0]}y{style_config.cover_size[1]}"
            )
            song_name = safe_filename(track['name'])
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{song_name}.jpg")

            if not os.path.exists(filepath):
                img_data = requests.get(cover_url).content
                with open(filepath, 'wb') as f:
                    f.write(img_data)
            cover_paths.append(filepath)
        except:
            continue

    # 生成封面拼贴
    if cover_paths:
        images = [Image.open(p).resize(style_config.tile_size) for p in cover_paths]
        cols = int(sqrt(len(images)))
        rows = (len(images) + cols - 1) // cols

        collage = Image.new('RGB',
                            (style_config.tile_size[0] * cols,
                             style_config.tile_size[1] * rows),
                            (255, 255, 255))

        for i, img in enumerate(images):
            x = (i % cols) * style_config.tile_size[0]
            y = (i // cols) * style_config.tile_size[1]
            collage.paste(img, (x, y))

        collage_path = os.path.join(app.config['UPLOAD_FOLDER'], 'collage.jpg')
        collage.save(collage_path)
    else:
        collage_path = None

    return {
        'playlist_info': playlist_info,
        'tracks': tracks,
        'collage_path': collage_path
    }


# -------------------- 路由处理 --------------------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    global key, content, prompt
    try:
        # 获取表单数据
        playlist_id = request.form['playlist_id']
        user_cookie = request.form['cookie']

        # 处理歌单
        result = process_playlist(playlist_id, user_cookie)
        tracks = result['tracks']
        playlist_info = result['playlist_info']

        # 准备分析内容
        track_list = "\n".join(
            f"{i + 1}. {t['name']} - {', '.join(ar['name'] for ar in t['ar'])}"
            for i, t in enumerate(tracks)
        )

        # 生成DeepSeek分析
        analysis_prompts = {
            "style_analysis": "请分析这个歌单的音乐风格和受众特征：",
            "cover_analysis": "根据封面拼贴分析这些封面的视觉风格一致性：",
            "trend_analysis": "结合最新音乐趋势对这些歌曲进行点评："
        }

        analyses = {}
        for key, prompt in analysis_prompts.items():
            content = f"歌单名称：{playlist_info['name']}\n歌曲列表：\n{track_list}"
        if key == 'cover_analysis' and result['collage_path']:
            content += "\n封面拼贴已生成，请分析视觉风格"
        analyses[key] = analyze_with_deepseek(content, prompt)

        # 构造返回结果
        return jsonify({
            'success': True,
            'playlist_info': {
                'name': playlist_info['name'],
                'creator': playlist_info['creator']['nickname'],
                'track_count': playlist_info['trackCount'],
                'play_count': playlist_info['playCount'],
                'description': playlist_info.get('description', '')
            },
            'tracks': [{
                'name': t['name'],
                'artists': [ar['name'] for ar in t['ar']],
                'album': t['al']['name']
            } for t in tracks],
            'collage_url': f"/uploads/{os.path.basename(result['collage_path'])}" if result['collage_path'] else None,
            'analyses': analyses
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)