from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os
from datetime import datetime

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# ----------------------------------------------------
# CORS（クロスオリジンリソース共有）ミドルウェアを追加
# これがCORSエラーを解決します
# ----------------------------------------------------
origins = ["*"]  # すべてのオリジンからのアクセスを許可

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # すべてのHTTPメソッド（GET, POSTなど）を許可
    allow_headers=["*"], # すべてのHTTPヘッダーを許可
)
# ----------------------------------------------------

# MongoDBへの接続
client = MongoClient(os.environ.get("MONGO_URL"))
db = client[os.environ.get("DB_NAME")]
collection = db["reservations"]

# ヘルスチェック用のエンドポイント
@app.get("/api/health")
def health_check():
    return {"status": "OK"}

# 予約情報を取得するエンドポイント
@app.get("/api/reservations")
def get_reservations(date: str):
    reservations = list(collection.find({"date": date}))
    for reservation in reservations:
        reservation["_id"] = str(reservation["_id"])
    return reservations
