import os

def read_config():
    """
    从项目根目录的config.ini文件读取配置
    格式：
    第一行：API_KEY
    第二行：MODEL_NAME
    
    Returns:
        dict: 包含api_key和model_name的字典
    """
    # 获取项目根目录路径（dev目录的父目录）
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..', 'config.ini')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 确保文件至少有两行
        if len(lines) < 2:
            raise ValueError("config.ini文件格式错误，至少需要两行：第一行API_KEY，第二行MODEL_NAME")
        
        api_key = lines[0].strip()
        model_name = lines[1].strip()
        
        if not api_key:
            raise ValueError("API_KEY不能为空")
        
        if not model_name:
            model_name = "qwen-turbo"  # 默认模型
        
        return {
            "api_key": api_key,
            "model_name": model_name
        }
    except FileNotFoundError:
        raise FileNotFoundError(f"未找到config.ini文件，请在项目根目录创建该文件，格式：\nAPI_KEY\nMODEL_NAME")
    except Exception as e:
        raise Exception(f"读取配置文件失败：{str(e)}")