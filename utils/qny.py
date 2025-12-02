import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))  # 定位到项目根目录
from config.config_read import configReader
from qiniu import Auth, put_file, etag,put_file_v2
import requests

class Qny:
    def __init__(self):
        self.AccessKey = configReader.get('qny.AccessKey')
        self.SecretKey = configReader.get('qny.SecretKey')
        self.Bucket = configReader.get('qny.Bucket')
        self.Domain = configReader.get('qny.Domain')
        self.Zone = configReader.get('qny.Zone')
        self.auth = Auth(self.AccessKey, self.SecretKey)

    def upload_file(self, local_path: str, key: str):
        token = self.auth.upload_token(self.Bucket, key, 3600)
        ret, info = put_file_v2(token, key, local_path)
        if ret is not None and ret['key'] == key:
            return f"{self.Domain}/{key}"
        else:
            raise Exception(f"Upload failed: {info}")

    def get_file_content(self, key: str):
        url = self.auth.private_download_url(f"{self.Domain}/{key}", expires=3600)
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"Download failed: {response.status_code}")

qny = Qny()

if __name__ == '__main__':
    print(qny.AccessKey)
    print(qny.SecretKey)
    print(qny.Bucket)
    print(qny.Domain)
    print(qny.Zone)

    ssss=qny.upload_file('test.png', 'testHtml.png')
    print("sssss",ssss)



