# クリーンベンチ予約システム

実験室のクリーンベンチをオンラインで予約できるシステムです。

## 特徴

- 🇯🇵 **完全日本語対応**: すべてのUIが日本語
- ⏰ **30分刻み予約**: 7:00-22:00の時間範囲で30分刻みの精密な時間管理
- 📅 **タイムテーブル表示**: 見やすいカレンダー形式の可視化
- 🚫 **ダブルブッキング防止**: 重複予約を自動防止
- 🗑️ **安全な削除機能**: 編集フォームから安全に削除
- 🌐 **クラウドデータベース**: MongoDB Atlas使用
- 🔄 **自動リトライ**: 接続エラー時の自動復旧機能
- 🧹 **データクリーンアップ**: 古いデータの自動削除

## 技術スタック

- **フロントエンド**: React 18 + Tailwind CSS + Axios
- **バックエンド**: FastAPI (Python) + Pydantic
- **データベース**: MongoDB Atlas
- **デプロイ**: Vercel
- **時間処理**: JST (日本標準時) 対応

## 本番環境

🌐 **デプロイ済みURL**: [Vercelでデプロイ済み]

## ローカル開発

### 前提条件

- Node.js 16+ 
- Python 3.9+
- MongoDB Atlas アカウント

### 環境変数設定

#### backend/.env
```bash
MONGO_URL="mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority"
DB_NAME="bench_reservation"
```

#### frontend/.env
```bash
REACT_APP_BACKEND_URL="[http://localhost:8001](https://clean-bench-reservation-2.vercel.app)"
```

### 開発サーバー起動

#### 1. バックエンド
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

#### 2. フロントエンド
```bash
cd frontend
npm install
npm start
```

## 使用方法

### 基本操作
1. **新規予約**: 「新規予約」ボタンから予約作成
2. **予約編集**: 予約バーをクリックして編集画面を開く
3. **予約削除**: 編集フォーム内の「🗑️ 予約削除」ボタン
4. **日付切り替え**: 前日/翌日ボタンで日付変更
5. **手動更新**: 「🔄 更新」ボタンで即座に最新データ取得

### メンテナンス
- **データクリーンアップ**: 「🧹 古いデータ削除」で30日より古い予約を削除

### 予約ルール
- **利用時間**: 7:00-22:00
- **時間単位**: 30分刻み
- **利用者名**: 1-50文字（特殊文字不可）
- **ベンチ**: 手前・奥の2台

## API仕様

### エンドポイント一覧

```
GET    /api/                    # システム情報
GET    /api/health             # ヘルスチェック
GET    /api/reservations       # 予約一覧取得
POST   /api/reservations       # 予約作成
GET    /api/reservations/{id}  # 予約詳細取得
PUT    /api/reservations/{id}  # 予約更新
DELETE /api/reservations/{id}  # 予約削除
GET    /api/benches            # ベンチ情報
POST   /api/cleanup/old-data   # 古いデータ削除
GET    /api/cleanup/status     # データベース状況
```

## 安全機能

### セキュリティ
- 入力値検証（長さ・文字種制限）
- SQLインジェクション対策
- XSS対策

### 信頼性
- 自動リトライ機能（最大3回）
- 接続監視・自動復旧
- タイムアウト処理
- エラーログ記録

### データ管理
- 過去データ自動削除
- データベース容量最適化
- バックアップ対応（MongoDB Atlas）

## トラブルシューティング

### よくある問題

1. **予約が読み込めない**
   - 「🔄 更新」ボタンを試す
   - ネットワーク接続を確認

2. **予約作成に失敗**
   - 時間範囲（7:00-22:00）を確認
   - 重複予約がないか確認

3. **削除ができない**
   - 編集フォーム内の削除ボタンを使用
   - 確認ダイアログで「OK」を選択

## 開発情報

### ディレクトリ構造
```
/
├── backend/           # FastAPI アプリケーション
│   ├── server.py     # メインアプリケーション
│   ├── .env          # 環境変数
│   └── requirements.txt
├── frontend/         # React アプリケーション  
│   ├── src/
│   │   ├── App.js    # メインコンポーネント
│   │   └── App.css   # スタイルシート
│   ├── package.json  # 依存関係
│   └── public/
├── vercel.json       # Vercel設定
└── README.md
```

### 開発コマンド
```bash
# 依存関係更新
cd frontend && npm update
cd backend && pip install -r requirements.txt

# ビルドテスト
cd frontend && npm run build

# コード品質チェック
cd frontend && npm run test
```

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

---

**🎯 このシステムで実験室の予約管理を効率化しましょう！**
