from http.server import BaseHTTPRequestHandler
import json
import os
import cv2
import numpy as np
import base64
from io import BytesIO
import tempfile
from urllib.parse import parse_qs

# 一時ディレクトリを作成
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'object_extractor')
os.makedirs(TEMP_DIR, exist_ok=True)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # コンテンツの長さを取得
        content_length = int(self.headers['Content-Length'])
        # リクエストボディを読み込む
        post_data = self.rfile.read(content_length)
        
        # multipart/form-dataの解析
        boundary = self.headers['Content-Type'].split('=')[1].encode()
        
        # バイナリデータから画像部分を抽出
        parts = post_data.split(boundary)
        image_data = None
        
        for part in parts:
            if b'Content-Disposition' in part and b'filename' in part:
                # ヘッダーとコンテンツの区切り
                header_end = part.find(b'\r\n\r\n')
                if header_end != -1:
                    # 画像データを取得
                    image_data = part[header_end + 4:]
                    break
        
        if not image_data:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No image provided'}).encode())
            return
        
        try:
            # 画像をOpenCVで処理
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise Exception("Invalid image format")
            
            # グレースケール変換
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 二値化処理
            _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
            
            # 輪郭検出
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            objects = []
            for i, contour in enumerate(contours):
                # 小さすぎる輪郭は無視
                if cv2.contourArea(contour) < 500:
                    continue
                
                # バウンディングボックスを取得
                x, y, w, h = cv2.boundingRect(contour)
                
                # オブジェクトを切り出し
                obj_img = img[y:y+h, x:x+w]
                
                # 透明化処理のためにアルファチャンネルを追加
                obj_rgba = cv2.cvtColor(obj_img, cv2.COLOR_BGR2BGRA)
                
                # 一時ファイルに保存
                obj_id = f"object-{i+1}"
                obj_path = os.path.join(TEMP_DIR, f"{obj_id}.png")
                cv2.imwrite(obj_path, obj_rgba)
                
                # サムネイル用にBase64エンコード
                _, buffer = cv2.imencode('.png', obj_rgba)
                obj_base64 = base64.b64encode(buffer).decode('utf-8')
                
                objects.append({
                    'id': obj_id,
                    'width': w,
                    'height': h,
                    'path': obj_path,
                    'base64': obj_base64
                })
            
            # レスポンス
            response = {'objects': objects}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())
