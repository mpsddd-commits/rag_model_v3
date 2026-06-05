from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from src import apis 
import importlib
import pkgutil


def run():
    app = FastAPI(servers=[
        {"url": "/", "description": "API 기본 서버"}
    ])
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
    origins = ["http://localhost" ]
    app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )

    return app

