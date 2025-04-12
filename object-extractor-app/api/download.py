from http.server import BaseHTTPRequestHandler
import os
import tempfile
from PIL import Image
from urllib.parse import parse_qs
import io

# 一時ディレクトリを設定
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'object_extractor')

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # パスからオブジェクトIDを取得
        path_parts = self.path.split('/')
        if len(path_parts) < 3:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'Invalid path')
            return
        
        obj_id = path_parts[2].split('?')[0] if '?' in path_parts[2] else path_parts[2]
        
        # クエリパラメータを解析
        query_params = {}
        if '?' in self.path:
            query_string = self.path.split('?')[1]
            query_parts = query_string.split('&')
            for part in query_parts:
                if '=' in part:
                    key, value = part.split('=')
                    query_params[key] = value
        
        bg_type = query_params.get('bg', 'transparent')
        bg_color = query_params.get('color', '%23FFFFFF').replace('%23', '#')  # URLエンコードされた#を戻す
        
        # オブジェクト画像のパス
        obj_path = os.path.join(TEMP_DIR, f"{obj_id}.png")
        
        if not os.path.exists(obj_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Object not found')
            return
        
        try:
            # 画像を読み込み
            img = Image.open(obj_path).convert('RGBA')
            
            # 背景処理
            if bg_type == 'white':
                background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(background, img).convert('RGB')
            elif bg_type == 'custom' and bg_color:
                try:
                    r = int(bg_color[1:3], 16)
                    g = int(bg_color[3:5], 16)
                    b = int(bg_color[5:7], 16)
                    background = Image.new('RGBA', img.size, (r, g, b, 255))
                    img = Image.alpha_composite(background, img).convert('RGB')
                except:
                    pass
            
            # 画像をバイナリデータに変換
            img_io = io.BytesIO()
            if bg_type == 'transparent':
                img.save(img_io, 'PNG')
                content_type = 'image/png'
                file_ext = 'png'
            else:
                img.save(img_io, 'JPEG', quality=95)
                content_type = 'image/jpeg'
                file_ext = 'jpg'
            img_io.seek(0)
            
            # レスポンスヘッダー
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header('Content-Disposition', f'attachment; filename="{obj_id}.{file_ext}"')
            self.end_headers()
            
            # 画像データをレスポンスとして送信
            self.wfile.write(img_io.getvalue())
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())