import yaml
import sys
import os
class ConfigReader:
    def __init__(self, config_path=os.path.join(os.path.dirname(__file__),'config.yaml')):
        with open(config_path, 'r',encoding='utf-8') as file:
            self.config = yaml.safe_load(file)

    def get(self, key, default=None):
        keys = key.split('.')
        current = self.config
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current

    def get_section(self, section):
        return self.config.get(section, {})

configReader=ConfigReader()

if __name__=='__main__':
   print(os.getcwd())
   print(os.path.join(os.getcwd(),'config.yaml'))
   print(configReader)
   print(configReader.get('siliconflow.url'))