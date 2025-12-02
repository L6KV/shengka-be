import json
import os
from typing import Any, Optional, TypeVar, cast

T = TypeVar('T')

class ConfigReader:
    def __init__(self):
        # 获取当前文件所在的目录
        current_dir = os.path.dirname(os.path.abspath(__file__))

        # 配置文件的路径
        config_file_path = os.path.join(current_dir, 'api_key.json')
        self.config = {}
        try:
            with open(config_file_path, 'r') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            print(f"警告: 配置文件 {config_file_path} 不存在，将使用默认配置")
        except json.JSONDecodeError:
            print(f"警告: 配置文件 {config_file_path} 格式无效，将使用默认配置")

    def get(self, key: str, default: Any = None, cast: Optional[type] = None) -> Any:
        """
        从配置中获取值

        参数:
            key: 配置键
            default: 默认值
            cast: 转换类型

        返回:
            配置值
        """
        value = self.config.get(key, default)

        # 转换类型
        if cast is not None and value is not None:
            try:
                if cast == bool:
                    # 特殊处理布尔值
                    if isinstance(value, str):
                        return value.lower() in ('true', 'yes', '1', 'y')
                    return bool(value)
                return cast(value)
            except (ValueError, TypeError):
                print(f"警告: 无法将值 '{value}' 转换为 {cast.__name__} 类型，将使用默认值 {default}")
                return default

        return value

my_read_configer=ConfigReader()
if __name__ == "__main__":
    config_reader = ConfigReader()
    print(f"调试模式: {config_reader.get('app', 'debug', default=True, cast=bool)}")
    print(f"主机: {config_reader.get('app', 'host', default='0.0.0.0')}")
    print(f"端口: {config_reader.get('app', 'port', default=8000, cast=int)}")

def get_api_key(key_name: str) -> Optional[str]:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_file_path = os.path.join(current_dir, 'api_key.json')
    try:
        with open(config_file_path, 'r') as f:
            config = json.load(f)
            return config.get(key_name)
    except (FileNotFoundError, json.JSONDecodeError):
        return None