# run.py
from app import create_app

app = create_app()

if __name__ == "__main__":
    # 在 debug 模式下，Flask 会使用单线程，可能会影响后台任务的演示
    # 在生产环境中，应使用 Gunicorn 等 WSGI 服务器，并配置多个 worker
    app.run(debug=True, threaded=True)  # threaded=True 允许后台线程运行
