from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.middleware.cors import CORSMiddleware  # CORSミドルウェアのインポート
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import pytz
from dateutil import parser

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 環境変数の読み込み
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# --- FastAPIアプリケーションのインスタンスを作成 ---
app = FastAPI()

# --- CORSミドルウェアの設定 (最重要) ---
# アプリケーションの初期段階で、全てのルートが定義される前に設定します。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # すべてのオリジンを許可
    allow_credentials=True,
    allow_methods=["*"],  # すべてのメソッドを許可
    allow_headers=["*"],  # すべてのヘッダーを許可
)
# ------------------------------------

# MongoDBへの接続設定
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=10,
    minPoolSize=2,
    maxIdleTimeMS=60000,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    socketTimeoutMS=15000,
    retryWrites=True,
    retryReads=True,
    heartbeatFrequencyMS=30000,
    maxConnecting=2
)
db = client[os.environ['DB_NAME']]

connection_status = {
    "healthy": True,
    "last_check": datetime.now(pytz.timezone('Asia/Tokyo')).isoformat()
}
JST = pytz.timezone('Asia/Tokyo') # JSTをグローバルに定義

async def check_database_connection():
    """データベース接続を確認"""
    global connection_status
    try:
        start_time = datetime.now()
        await asyncio.wait_for(client.admin.command('ping'), timeout=3.0)
        response_time = (datetime.now() - start_time).total_seconds()
        
        connection_status["healthy"] = True
        connection_status["last_check"] = datetime.now(JST).isoformat()
        logger.info(f"データベース接続確認成功: {response_time:.3f}秒")
        return True
        
    except Exception as e:
        connection_status["healthy"] = False
        connection_status["last_check"] = datetime.now(JST).isoformat()
        logger.error(f"データベース接続確認失敗: {str(e)}")
        return False

async def ensure_database_connection():
    """データベース接続を保証"""
    if not connection_status["healthy"]:
        logger.info("データベース再接続を試行")
        return await check_database_connection()
    return True

# APIルーターの作成
api_router = APIRouter()

# Pydanticモデルの定義 (変更なし、内容は省略)
class ReservationCreate(BaseModel):
    bench_id: str
    user_name: str
    start_time: str
    end_time: str
    
    @validator('bench_id')
    def validate_bench_id(cls, v):
        if v not in ['front', 'back']:
            raise ValueError('bench_id must be either "front" or "back"')
        return v
    
    @validator('user_name')
    def validate_user_name(cls, v):
        if not v or not v.strip():
            raise ValueError('user_name is required')
        v = v.strip()
        if len(v) < 1 or len(v) > 50:
            raise ValueError('利用者名は1文字以上50文字以下で入力してください')
        import re
        if re.search(r'[<>"\'\&]', v):
            raise ValueError('利用者名に使用できない文字が含まれています')
        return v
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        try:
            dt = parser.parse(v)
            if dt.tzinfo is None:
                dt = JST.localize(dt)
            return dt.astimezone(JST).isoformat()
        except Exception as e:
            raise ValueError(f'Invalid time format: {str(e)}')

class Reservation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bench_id: str
    user_name: str
    start_time: str
    end_time: str
    created_at: str = Field(default_factory=lambda: datetime.now(JST).isoformat())
    
class ReservationUpdate(BaseModel):
    user_name: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        if v is not None:
            try:
                dt = parser.parse(v)
                if dt.tzinfo is None:
                    dt = JST.localize(dt)
                return dt.astimezone(JST).isoformat()
            except Exception as e:
                raise ValueError(f'Invalid time format: {str(e)}')
        return v


# ユーティリティ関数 (変更なし、内容は省略)
def parse_jst_time(time_str: str) -> datetime:
    dt = parser.parse(time_str)
    if dt.tzinfo is None:
        dt = JST.localize(dt)
    return dt.astimezone(JST)

def check_time_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    dt_start1 = parse_jst_time(start1)
    dt_end1 = parse_jst_time(end1)
    dt_start2 = parse_jst_time(start2)
    dt_end2 = parse_jst_time(end2)
    return dt_start1 < dt_end2 and dt_start2 < dt_end1

async def check_double_booking(bench_id: str, start_time: str, end_time: str, exclude_id: str = None) -> bool:
    query = {"bench_id": bench_id}
    if exclude_id:
        query["id"] = {"$ne": exclude_id}
    
    existing_reservations = await db.reservations.find(query).to_list(1000)
    
    for reservation in existing_reservations:
        if check_time_overlap(start_time, end_time, reservation['start_time'], reservation['end_time']):
            return True
    
    return False

# --- APIルートの定義 (変更なし、内容は省略) ---
@api_router.get("/")
async def root():
    return {"message": "ベンチ予約システム API", "current_time_jst": datetime.now(JST).isoformat()}

@api_router.get("/health")
async def health_check():
    try:
        start_time = datetime.now()
        await asyncio.wait_for(
            db.reservations.find_one(),
            timeout=5.0
        )
        response_time = (datetime.now() - start_time).total_seconds()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(JST).isoformat(),
            "database": "connected",
            "database_response_time": f"{response_time:.3f}s"
        }
    except asyncio.TimeoutError:
        logger.error("ヘルスチェック: データベース接続タイムアウト")
        raise HTTPException(status_code=503, detail="データベース接続タイムアウト")
    except Exception as e:
        logger.error(f"ヘルスチェック: {str(e)}")
        raise HTTPException(status_code=503, detail=f"システムエラー: {str(e)}")

@api_router.post("/reservations", response_model=Reservation)
async def create_reservation(reservation_data: ReservationCreate):
    start_dt = parse_jst_time(reservation_data.start_time)
    end_dt = parse_jst_time(reservation_data.end_time)
    
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="終了時刻は開始時刻より後である必要があります")
    
    if start_dt.hour < 7 or start_dt.hour >= 22 or end_dt.hour < 7 or end_dt.hour > 22:
        raise HTTPException(status_code=400, detail="予約可能時間は7:00-22:00です")
    
    if start_dt.minute not in [0, 30] or end_dt.minute not in [0, 30]:
        raise HTTPException(status_code=400, detail="時刻は30分刻みで入力してください (例: 07:00, 07:30, 08:00)")
    
    if await check_double_booking(reservation_data.bench_id, reservation_data.start_time, reservation_data.end_time):
        raise HTTPException(status_code=409, detail="この時間帯は既に予約されています")
    
    reservation = Reservation(**reservation_data.dict())
    await db.reservations.insert_one(reservation.dict())
    return reservation

@api_router.get("/reservations", response_model=List[Reservation])
async def get_reservations(date: Optional[str] = None, bench_id: Optional[str] = None):
    logger.info(f"=== 予約取得リクエスト開始 ===")
    logger.info(f"日付: {date}, ベンチID: {bench_id}")
    
    if not await ensure_database_connection():
        raise HTTPException(status_code=503, detail="データベース接続に問題があります。しばらく待ってから再試行してください。")
    
    try:
        query = {}
        if bench_id:
            if bench_id not in ['front', 'back']:
                raise HTTPException(status_code=400, detail="無効なベンチIDです")
            query["bench_id"] = bench_id
        
        if date:
            try:
                date_obj = parser.parse(date).date()
                min_date = datetime.now().date() - timedelta(days=30)
                if date_obj < min_date:
                    logger.info(f"古すぎる日付のリクエスト: {date}")
                    return []
                
                start_of_day = JST.localize(datetime.combine(date_obj, datetime.min.time()))
                end_of_day = JST.localize(datetime.combine(date_obj, datetime.max.time()))
                
                query["start_time"] = {
                    "$gte": start_of_day.isoformat(),
                    "$lt": end_of_day.isoformat()
                }
                logger.info(f"日付フィルター: {start_of_day.isoformat()} - {end_of_day.isoformat()}")
                
            except Exception as date_error:
                logger.error(f"日付解析エラー: {str(date_error)}")
                raise HTTPException(status_code=400, detail="無効な日付形式です")
        
        logger.info(f"MongoDB クエリ: {query}")
        
        reservations = []
        for attempt in range(3):
            try:
                logger.info(f"データベースクエリ実行（試行 {attempt + 1}/3）")
                reservations = await asyncio.wait_for(
                    db.reservations.find(query).to_list(500),
                    timeout=5.0 + (attempt * 2)
                )
                logger.info(f"取得された予約数: {len(reservations)}")
                break
            except asyncio.TimeoutError:
                logger.warning(f"データベースクエリタイムアウト（試行 {attempt + 1}）")
                if attempt == 2:
                    connection_status["healthy"] = False
                    raise HTTPException(
                        status_code=504, 
                        detail="データベースの応答が遅くなっています。しばらく待ってから再試行してください。"
                    )
                await asyncio.sleep(1)
            except Exception as db_error:
                logger.error(f"データベースエラー（試行 {attempt + 1}）: {str(db_error)}")
                if attempt == 2:
                    connection_status["healthy"] = False
                    raise HTTPException(
                        status_code=500, 
                        detail="データベースエラーが発生しました。システム管理者にお問い合わせください。"
                    )
                await asyncio.sleep(1)
        
        try:
            valid_reservations = []
            for reservation in reservations:
                if all(key in reservation for key in ['id', 'bench_id', 'user_name', 'start_time', 'end_time']):
                    valid_reservations.append(reservation)
                else:
                    logger.warning(f"無効な予約データを検出: {reservation}")
            
            valid_reservations.sort(key=lambda x: x['start_time'])
            logger.info(f"有効な予約数: {len(valid_reservations)}")
            
            return [Reservation(**reservation) for reservation in valid_reservations]
        except Exception as process_error:
            logger.error(f"データ処理エラー: {str(process_error)}")
            raise HTTPException(status_code=500, detail="予約データの処理中にエラーが発生しました")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"=== 予約取得処理中に予期しないエラー発生 ===")
        logger.error(f"エラー内容: {str(e)}")
        logger.error(f"エラータイプ: {type(e)}")
        connection_status["healthy"] = False
        raise HTTPException(
            status_code=500, 
            detail="予約取得処理中に予期しないエラーが発生しました。しばらく待ってから再試行してください。"
        )

@api_router.get("/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    reservation = await db.reservations.find_one({"id": reservation_id})
    if not reservation:
        raise HTTPException(status_code=404, detail="予約が見つかりません")
    return Reservation(**reservation)

@api_router.put("/reservations/{reservation_id}", response_model=Reservation)
async def update_reservation(reservation_id: str, update_data: ReservationUpdate):
    existing = await db.reservations.find_one({"id": reservation_id})
    if not existing:
        raise HTTPException(status_code=404, detail="予約が見つかりません")
    
    update_dict = {}
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            update_dict[field] = value
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="更新するデータがありません")
    
    start_time = update_dict.get('start_time', existing['start_time'])
    end_time = update_dict.get('end_time', existing['end_time'])
    
    start_dt = parse_jst_time(start_time)
    end_dt = parse_jst_time(end_time)
    
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="終了時刻は開始時刻より後である必要があります")
    
    if await check_double_booking(existing['bench_id'], start_time, end_time, reservation_id):
        raise HTTPException(status_code=409, detail="この時間帯は既に予約されています")
    
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": update_dict}
    )
    
    updated_reservation = await db.reservations.find_one({"id": reservation_id})
    return Reservation(**updated_reservation)

@api_router.delete("/reservations/{reservation_id}")
async def delete_reservation(reservation_id: str):
    logger.info(f"=== 削除リクエスト受信 ===")
    logger.info(f"reservation_id: {reservation_id}")
    logger.info(f"リクエストタイプ: DELETE")
    
    try:
        existing = await db.reservations.find_one({"id": reservation_id})
        logger.info(f"既存予約検索結果: {existing}")
        
        if not existing:
            logger.warning(f"削除対象の予約が見つかりません: id={reservation_id}")
            raise HTTPException(status_code=404, detail="予約が見つかりません")
        
        logger.info(f"削除対象予約詳細: {existing}")
        
        result = await db.reservations.delete_one({"id": reservation_id})
        logger.info(f"削除実行結果: deleted_count={result.deleted_count}")
        
        if result.deleted_count == 0:
            logger.error(f"削除操作に失敗しました: id={reservation_id}")
            raise HTTPException(status_code=500, detail="削除操作に失敗しました")
        
        logger.info(f"=== 予約削除成功 ===")
        logger.info(f"削除済みID: {reservation_id}")
        
        return {
            "message": "予約が削除されました", 
            "deleted_id": reservation_id,
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"=== 削除処理中にエラー発生 ===")
        logger.error(f"エラー内容: {str(e)}")
        logger.error(f"エラータイプ: {type(e)}")
        raise HTTPException(status_code=500, detail=f"削除処理中にエラーが発生しました: {str(e)}")

@api_router.get("/benches")
async def get_benches():
    return {
        "benches": [
            {"id": "front", "name": "手前"},
            {"id": "back", "name": "奥"}
        ]
    }

@api_router.post("/cleanup/old-data")
async def cleanup_old_data(days_to_keep: int = 30):
    if days_to_keep < 7:
        raise HTTPException(status_code=400, detail="保持期間は最低7日必要です")
    
    logger.info(f"=== 古いデータクリーンアップ開始 ===")
    logger.info(f"保持期間: {days_to_keep}日")
    
    try:
        if not await ensure_database_connection():
            raise HTTPException(status_code=503, detail="データベース接続に問題があります")
        
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        cutoff_jst = JST.localize(cutoff_date.replace(hour=0, minute=0, second=0, microsecond=0))
        logger.info(f"削除基準日時: {cutoff_jst.isoformat()}")
        
        query = {"start_time": {"$lt": cutoff_jst.isoformat()}}
        old_reservations = await db.reservations.find(query).to_list(1000)
        logger.info(f"削除対象の予約数: {len(old_reservations)}")
        
        if len(old_reservations) == 0:
            return {
                "message": "削除対象のデータはありません",
                "deleted_count": 0,
                "cutoff_date": cutoff_jst.isoformat()
            }
        
        delete_result = await db.reservations.delete_many(query)
        deleted_count = delete_result.deleted_count
        
        logger.info(f"削除完了: {deleted_count}件")
        
        return {
            "message": f"古い予約データを削除しました",
            "deleted_count": deleted_count,
            "cutoff_date": cutoff_jst.isoformat(),
            "days_kept": days_to_keep
        }
        
    except Exception as e:
        logger.error(f"データクリーンアップエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"データクリーンアップ中にエラーが発生しました: {str(e)}")

@api_router.get("/cleanup/status")
async def cleanup_status():
    try:
        if not await ensure_database_connection():
            raise HTTPException(status_code=503, detail="データベース接続に問題があります")
        
        total_count = await db.reservations.count_documents({})
        
        today = datetime.now().date()
        today_jst = JST.localize(datetime.combine(today, datetime.min.time()))
        future_count = await db.reservations.count_documents({
            "start_time": {"$gte": today_jst.isoformat()}
        })
        
        past_count = total_count - future_count
        
        cutoff_30_days = datetime.now() - timedelta(days=30)
        cutoff_30_jst = JST.localize(cutoff_30_days.replace(hour=0, minute=0, second=0, microsecond=0))
        old_count = await db.reservations.count_documents({
            "start_time": {"$lt": cutoff_30_jst.isoformat()}
        })
        
        return {
            "total_reservations": total_count,
            "future_reservations": future_count,
            "past_reservations": past_count,
            "old_data_30days": old_count,
            "cleanup_recommended": old_count > 0,
            "database_status": "healthy" if connection_status["healthy"] else "unhealthy",
            "last_check": connection_status["last_check"]
        }
        
    except Exception as e:
        logger.error(f"ステータス取得エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"ステータス取得中にエラーが発生しました: {str(e)}")

# ルーターをメインアプリに含める
app.include_router(api_router)

# シャットダウンイベント
@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Vercelデプロイメント互換性のための設定
from mangum import Mangum

# Vercel用のハンドラを作成
handler = Mangum(app)
