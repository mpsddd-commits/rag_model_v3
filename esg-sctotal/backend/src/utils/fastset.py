from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from src.utils.settings import settings
from src import apis 
import importlib
import pkgutil
from contextlib import asynccontextmanager
from src.utils.kafkasv import startConsumer
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.staticfiles import StaticFiles

# [STARTUP] 앱이 켜질 때 Kafka 실행
@asynccontextmanager
async def lifespan(app: FastAPI):
    startConsumer() 
    print("🚀 Kafka Email Consumer Started...")
    yield
    
def run():
    app = FastAPI(servers=[
        {"url": "/", "description": "API 기본 서버"}
    ], lifespan=lifespan)
    # 라우터 등록
    for _, module_name, _ in pkgutil.iter_modules(apis.__path__):
        module = importlib.import_module(f"src.apis.{module_name}")
        if hasattr(module, "router"):
            app.include_router(
                module.router,
                prefix=f"/{module_name}",
                tags=[module_name]
            )

    # CORS 설정
    origins = ["http://localhost:80", settings.host_ip, "http://192.168.0.106", "http://192.168.0.105" ]
    app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

    # # Static Files
    # app.mount("/static", StaticFiles(directory="static"), name="static")
    Instrumentator().instrument(app).expose(app)
    return app
