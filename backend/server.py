from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import pytz
from dateutil import parser
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection with improved connection pooling
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(
    mongo_url,
    maxPoolSize=10,           # 接続プール削減（無料プランに配慮）
    minPoolSize=2,            # 最小接続数
    maxIdleTimeMS=60000,      # アイドル接続のタイムアウト (1分)
    serverSelectionTimeoutMS=5000,  # サーバー選択タイムアウト (5秒)
    connectTimeoutMS=10000,   # 接続タイムアウト (10秒)
    socketTimeoutMS=15000,    # ソケットタイムアウト (15秒)
    retryWrites=True,         # 書き込みリトライ
    retryReads=True,          # 読み込みリトライ追加
    heartbeatFrequencyMS=30000,  # ハートビート頻度 (30秒)
    maxConnecting=2           # 同時接続試行数制限
)
db = client[os.environ['DB_NAME']]

async def check_database_connection():
    """データベース接続を確認し、必要に応じて再接続"""
    global connection_status
    try:
        start_time = datetime.now()
        # 軽量なping操作
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

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Japan Standard Time timezone
JST = pytz.timezone('Asia/Tokyo')

# Define Models
class ReservationCreate(BaseModel):
    bench_id: str  # "front" or "back"
    user_name: str
    start_time: str  # ISO format string
    end_time: str    # ISO format string
    
    @validator('bench_id')
    def validate_bench_id(cls, v):
        if v not in ['front', 'back']:
            raise ValueError('bench_id must be either "front" or "back"')
        return v
    
    @validator('user_name')
    def validate_user_name(cls, v):
        if not v or not v.strip():
            raise ValueError('user_name is required')
        return v.strip()
    
    @validator('start_time', 'end_time')
    def validate_time_format(cls, v):
        try:
            # Parse the time string and convert to JST
            dt = parser.parse(v)
            if dt.tzinfo is None:
                # If no timezone info, assume JST
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

# Utility functions for time handling
def parse_jst_time(time_str: str) -> datetime:
    """Parse time string and convert to JST datetime object"""
    dt = parser.parse(time_str)
    if dt.tzinfo is None:
        dt = JST.localize(dt)
    return dt.astimezone(JST)

def check_time_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Check if two time ranges overlap"""
    dt_start1 = parse_jst_time(start1)
    dt_end1 = parse_jst_time(end1)
    dt_start2 = parse_jst_time(start2)
    dt_end2 = parse_jst_time(end2)
    
    # Two ranges overlap if one starts before the other ends
    return dt_start1 < dt_end2 and dt_start2 < dt_end1

async def check_double_booking(bench_id: str, start_time: str, end_time: str, exclude_id: str = None) -> bool:
    """Check if a reservation would conflict with existing reservations"""
    # Build query to find overlapping reservations
    query = {"bench_id": bench_id}
    if exclude_id:
        query["id"] = {"$ne": exclude_id}
    
    existing_reservations = await db.reservations.find(query).to_list(1000)
    
    for reservation in existing_reservations:
        if check_time_overlap(start_time, end_time, reservation['start_time'], reservation['end_time']):
            return True
    
    return False

# API Routes
@api_router.get("/")
async def root():
    return {"message": "ベンチ予約システム API", "current_time_jst": datetime.now(JST).isoformat()}

@api_router.get("/health")
async def health_check():
    """System health check endpoint"""
    try:
        # MongoDB接続テスト
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
    """Create a new reservation"""
    # Validate that end time is after start time
    start_dt = parse_jst_time(reservation_data.start_time)
    end_dt = parse_jst_time(reservation_data.end_time)
    
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="終了時刻は開始時刻より後である必要があります")
    
    # Validate time range (7:00-22:00)
    if start_dt.hour < 7 or start_dt.hour >= 22 or end_dt.hour < 7 or end_dt.hour > 22:
        raise HTTPException(status_code=400, detail="予約可能時間は7:00-22:00です")
    
    # Validate 30-minute increments
    if start_dt.minute not in [0, 30] or end_dt.minute not in [0, 30]:
        raise HTTPException(status_code=400, detail="時刻は30分刻みで入力してください (例: 07:00, 07:30, 08:00)")
    
    # Check for double booking
    if await check_double_booking(reservation_data.bench_id, reservation_data.start_time, reservation_data.end_time):
        raise HTTPException(status_code=409, detail="この時間帯は既に予約されています")
    
    # Create reservation
    reservation = Reservation(**reservation_data.dict())
    
    # Insert into database
    await db.reservations.insert_one(reservation.dict())
    
    return reservation

@api_router.get("/reservations", response_model=List[Reservation])
async def get_reservations(date: Optional[str] = None, bench_id: Optional[str] = None):
    """Get reservations, optionally filtered by date and/or bench_id"""
    logger.info(f"=== 予約取得リクエスト ===")
    logger.info(f"日付: {date}, ベンチID: {bench_id}")
    
    try:
        query = {}
        
        if bench_id:
            query["bench_id"] = bench_id
        
        if date:
            # Parse date and get start/end of day in JST
            try:
                date_obj = parser.parse(date).date()
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
        
        # Database query with timeout
        try:
            reservations = await asyncio.wait_for(
                db.reservations.find(query).to_list(1000),
                timeout=10.0  # 10秒タイムアウト
            )
            logger.info(f"取得された予約数: {len(reservations)}")
            
        except asyncio.TimeoutError:
            logger.error("データベースクエリタイムアウト")
            raise HTTPException(status_code=504, detail="データベースの応答がタイムアウトしました。しばらく待ってから再試行してください。")
        
        except Exception as db_error:
            logger.error(f"データベースエラー: {str(db_error)}")
            raise HTTPException(status_code=500, detail=f"データベースエラーが発生しました: {str(db_error)}")
        
        # Sort by start time
        reservations.sort(key=lambda x: x['start_time'])
        
        logger.info(f"=== 予約取得成功 ===")
        return [Reservation(**reservation) for reservation in reservations]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"=== 予約取得処理中にエラー発生 ===")
        logger.error(f"エラー内容: {str(e)}")
        logger.error(f"エラータイプ: {type(e)}")
        raise HTTPException(status_code=500, detail=f"予約取得処理中にエラーが発生しました: {str(e)}")

@api_router.get("/reservations/{reservation_id}", response_model=Reservation)
async def get_reservation(reservation_id: str):
    """Get a specific reservation"""
    reservation = await db.reservations.find_one({"id": reservation_id})
    if not reservation:
        raise HTTPException(status_code=404, detail="予約が見つかりません")
    
    return Reservation(**reservation)

@api_router.put("/reservations/{reservation_id}", response_model=Reservation)
async def update_reservation(reservation_id: str, update_data: ReservationUpdate):
    """Update a reservation"""
    # Get existing reservation
    existing = await db.reservations.find_one({"id": reservation_id})
    if not existing:
        raise HTTPException(status_code=404, detail="予約が見つかりません")
    
    # Prepare update data
    update_dict = {}
    for field, value in update_data.dict(exclude_unset=True).items():
        if value is not None:
            update_dict[field] = value
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="更新するデータがありません")
    
    # If updating times, validate them
    start_time = update_dict.get('start_time', existing['start_time'])
    end_time = update_dict.get('end_time', existing['end_time'])
    
    start_dt = parse_jst_time(start_time)
    end_dt = parse_jst_time(end_time)
    
    if start_dt >= end_dt:
        raise HTTPException(status_code=400, detail="終了時刻は開始時刻より後である必要があります")
    
    # Check for double booking (exclude current reservation)
    if await check_double_booking(existing['bench_id'], start_time, end_time, reservation_id):
        raise HTTPException(status_code=409, detail="この時間帯は既に予約されています")
    
    # Update reservation
    await db.reservations.update_one(
        {"id": reservation_id},
        {"$set": update_dict}
    )
    
    # Return updated reservation
    updated_reservation = await db.reservations.find_one({"id": reservation_id})
    return Reservation(**updated_reservation)

@api_router.delete("/reservations/{reservation_id}")
async def delete_reservation(reservation_id: str):
    """Delete a reservation"""
    logger.info(f"=== 削除リクエスト受信 ===")
    logger.info(f"reservation_id: {reservation_id}")
    logger.info(f"リクエストタイプ: DELETE")
    
    try:
        # 削除前に予約が存在するか確認
        existing = await db.reservations.find_one({"id": reservation_id})
        logger.info(f"既存予約検索結果: {existing}")
        
        if not existing:
            logger.warning(f"削除対象の予約が見つかりません: id={reservation_id}")
            raise HTTPException(status_code=404, detail="予約が見つかりません")
        
        logger.info(f"削除対象予約詳細: {existing}")
        
        # 予約を削除
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
    """Get available benches"""
    return {
        "benches": [
            {"id": "front", "name": "手前"},
            {"id": "back", "name": "奥"}
        ]
    }

@api_router.get("/current-time")
async def get_current_time():
    """Get current JST time"""
    return {"current_time_jst": datetime.now(JST).isoformat()}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()