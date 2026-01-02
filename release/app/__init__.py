from flask import Flask
from .routes import main, api

# 初始化Flask应用
def create_app(config_name=None):
    """创建并配置Flask应用"""
    app = Flask(__name__)
    
    # 配置应用
    app.config['SECRET_KEY'] = 'dev_secret_key'  # 开发环境使用，生产环境应使用环境变量
    
    # 注册蓝图
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)
    
    return app
