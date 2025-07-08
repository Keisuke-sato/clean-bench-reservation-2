import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

-const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
-const API = `${BACKEND_URL}/api`;
+// ---------- API エンドポイント生成 ----------
+// 1) 環境変数が無い場合は相対パスで /api 呼び出し
+// 2) 末尾の余分な / を除去
+const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/+$/, '');
+const API = `${BACKEND_URL ? BACKEND_URL : ''}/api`;
+
+// 共通 axios インスタンスを作成
+const api = axios.create({ baseURL: API });


const App = () => {
  const [reservations, setReservations] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingReservation, setEditingReservation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    bench_id: 'front',
    user_name: '',
    start_time: '',
    end_time: ''
  });

  // Load reservations for selected date with comprehensive error handling
  const loadReservations = async (retryCount = 0, maxRetries = 3) => {
    try {
      console.log(`予約読み込み開始 (試行 ${retryCount + 1}/${maxRetries + 1}):`, selectedDate);
      setLoading(true);
      setError(''); // エラーをクリア
      
      // リクエスト設定の最適化
      const requestConfig = {
        params: { date: selectedDate },
        timeout: 8000 + (retryCount * 2000), // 段階的にタイムアウトを延長
        validateStatus: function (status) {
          return status >= 200 && status < 300; // デフォルト
        },
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      };
      
      const response = await axios.get(`${API}/reservations`, requestConfig);
      
      // レスポンスデータの検証
      if (!Array.isArray(response.data)) {
        throw new Error('サーバーから無効なデータ形式が返されました');
      }
      
      // データの妥当性チェック
      const validReservations = response.data.filter(reservation => {
        return reservation && 
               reservation.id && 
               reservation.bench_id && 
               reservation.user_name && 
               reservation.start_time && 
               reservation.end_time;
      });
      
      if (validReservations.length !== response.data.length) {
        console.warn(`無効な予約データを除外: ${response.data.length - validReservations.length}件`);
      }
      
      console.log('予約データ取得成功:', validReservations);
      setReservations(validReservations);
      
    } catch (err) {
      console.error(`予約読み込みエラー (試行 ${retryCount + 1}):`, err);
      
      // エラー分類と自動リトライ判定
      const isRetryableError = (
        err.code === 'ECONNABORTED' || // タイムアウト
        err.code === 'NETWORK_ERROR' || // ネットワークエラー
        err.code === 'ERR_NETWORK' ||   // ネットワークエラー (axios)
        (err.response && err.response.status >= 500) || // サーバーエラー
        (err.response && err.response.status === 503) || // サービス利用不可
        (err.response && err.response.status === 504)    // タイムアウト
      );
      
      const shouldRetry = retryCount < maxRetries && isRetryableError;
      
      if (shouldRetry) {
        const delay = Math.min(1000 * (2 ** retryCount), 8000); // 最大8秒
        console.log(`${delay/1000}秒後に自動リトライします...`);
        setError(`接続中です... (${retryCount + 1}回目再試行中)`);
        
        setTimeout(() => {
          loadReservations(retryCount + 1, maxRetries);
        }, delay);
        
      } else {
        // 最大リトライ回数に達した場合またはリトライ不可エラー
        let errorMessage = '予約の読み込みに失敗しました';
        
        if (err.response) {
          // サーバーエラーレスポンスがある場合
          errorMessage = err.response.data?.detail || 
                        `サーバーエラー (${err.response.status})`;
        } else if (err.code === 'ECONNABORTED' || err.code === 'ERR_NETWORK') {
          errorMessage = 'ネットワーク接続に問題があります';
        } else if (err.message) {
          errorMessage = err.message;
        }
        
        setError(errorMessage);
        console.error('最大リトライ回数に達しました:', err);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReservations();
  }, [selectedDate]);

  // Create reservation
  const createReservation = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      
      const reservationData = {
        ...formData,
        start_time: `${selectedDate}T${formData.start_time}:00`,
        end_time: `${selectedDate}T${formData.end_time}:00`
      };
      
      await axios.post(`${API}/reservations`, reservationData);
      
      // Reset form and refresh
      setFormData({ bench_id: 'front', user_name: '', start_time: '', end_time: '' });
      setShowCreateForm(false);
      await loadReservations();
    } catch (err) {
      setError(err.response?.data?.detail || '予約の作成に失敗しました');
    } finally {
      setLoading(false);-const BACKEND_UR
    }
  };

  // Update reservation
  const updateReservation = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError('');
      
      const updateData = {
        user_name: formData.user_name,
        start_time: `${selectedDate}T${formData.start_time}:00`,
        end_time: `${selectedDate}T${formData.end_time}:00`
      };
      
      await axios.put(`${API}/reservations/${editingReservation.id}`, updateData);
      
      // Reset form and refresh
      setFormData({ bench_id: 'front', user_name: '', start_time: '', end_time: '' });
      setEditingReservation(null);
      await loadReservations();
    } catch (err) {
      setError(err.response?.data?.detail || '予約の更新に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  // Start editing
  const startEdit = (reservation) => {
    const startTime = new Date(reservation.start_time).toTimeString().substring(0, 5);
    const endTime = new Date(reservation.end_time).toTimeString().substring(0, 5);
    
    setFormData({
      bench_id: reservation.bench_id,
      user_name: reservation.user_name,
      start_time: startTime,
      end_time: endTime
    });
    setEditingReservation(reservation);
    setShowCreateForm(false);
  };

  // Date navigation
  const changeDate = (days) => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + days);
    setSelectedDate(newDate.toISOString().split('T')[0]);
  };

  // Format date for display
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ja-JP', { 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      weekday: 'long'
    });
  };

  // Generate time slots for timetable (every 30 minutes, 7:00-22:00)
  const generateTimeSlots = () => {
    const slots = [];
    for (let hour = 7; hour <= 22; hour++) {
      for (let minute = 0; minute < 60; minute += 30) {
        const timeString = `${hour.toString().padStart(2, '0')}:${minute.toString().padStart(2, '0')}`;
        slots.push(timeString);
      }
    }
    return slots;
  };

  // Calculate reservation bar properties
  const calculateBarProperties = (reservation) => {
    const startDate = new Date(reservation.start_time);
    const endDate = new Date(reservation.end_time);
    
    const startMinutes = startDate.getHours() * 60 + startDate.getMinutes();
    const endMinutes = endDate.getHours() * 60 + endDate.getMinutes();
    const durationMinutes = endMinutes - startMinutes;
    
    // 7:00 (420分) を基準点として調整
    const baseOffsetMinutes = 7 * 60; // 7:00 = 420分
    const adjustedStartMinutes = startMinutes - baseOffsetMinutes;
    
    // Each 30-minute slot is 40px high
    const pixelsPerMinute = 40 / 30;
    const top = adjustedStartMinutes * pixelsPerMinute;
    const height = durationMinutes * pixelsPerMinute;
    
    return { top, height };
  };

  // Get reservation color
  const getReservationColor = (index) => {
    const colors = [
      '#667eea', '#764ba2', '#f093fb', '#f5576c',
      '#4facfe', '#00f2fe', '#43e97b', '#38f9d7',
      '#ffecd2', '#fcb69f', '#a8edea', '#fed6e3'
    ];
    return colors[index % colors.length];
  };

  // Auto cleanup old data function
  const cleanupOldData = async () => {
    try {
      setLoading(true);
      setError('');
      
      const response = await axios.post(`${API}/cleanup/old-data`, {}, {
        timeout: 15000 // 15秒タイムアウト
      });
      
      console.log('クリーンアップ完了:', response.data);
      
      // 成功メッセージを表示
      if (response.data.deleted_count > 0) {
        alert(`✅ ${response.data.deleted_count}件の古い予約データを削除しました`);
      } else {
        alert('ℹ️ 削除対象のデータはありませんでした');
      }
      
      // 予約リストを更新
      await loadReservations();
      
    } catch (err) {
      console.error('クリーンアップエラー:', err);
      const errorMessage = err.response?.data?.detail || 'データクリーンアップに失敗しました';
      setError(`クリーンアップエラー: ${errorMessage}`);
    } finally {
      setLoading(false);
    }
  };

  const timeSlots = generateTimeSlots();

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>クリーンベンチ予約システム</h1>
          <p className="version-info">バージョン 2.0 - 改善版</p>
        </header>

        {/* Date Navigation */}
        <div className="date-navigation">
          <button onClick={() => changeDate(-1)} className="nav-button">
            ← 前日
          </button>
          <div className="current-date">
            {formatDate(selectedDate)}
          </div>
          <button onClick={() => changeDate(1)} className="nav-button">
            翌日 →
          </button>
        </div>

        {/* Create Reservation Button & Manual Refresh & Cleanup */}
        <div className="action-buttons">
          <button 
            onClick={() => {
              setShowCreateForm(true);
              setEditingReservation(null);
              setFormData({ bench_id: 'front', user_name: '', start_time: '', end_time: '' });
            }}
            className="create-button"
          >
            新規予約
          </button>
          
          <button 
            onClick={() => {
              console.log('手動更新ボタンがクリックされました');
              loadReservations(0, 3); // 手動更新時も自動リトライ機能を使用
            }}
            className="refresh-button"
            disabled={loading}
            title="予約一覧を手動で更新"
          >
            {loading ? '🔄 更新中...' : '🔄 更新'}
          </button>
          
          <button 
            onClick={() => {
              if (window.confirm('30日より古い予約データを削除します。\nこの操作は取り消せません。\n実行しますか？')) {
                cleanupOldData();
              }
            }}
            className="cleanup-button"
            disabled={loading}
            title="30日より古い予約データを削除してデータベース容量を節約"
          >
            {loading ? '🧹 削除中...' : '🧹 古いデータ削除'}
          </button>
        </div>

        {/* Error Message with Retry Option */}
        {error && (
          <div className="error-container">
            <div className="error-message">
              ⚠️ {error}
            </div>
            <button 
              onClick={() => {
                setError('');
                loadReservations(0, 3);
              }}
              className="retry-button"
              disabled={loading}
            >
              {loading ? '再試行中...' : '🔄 再試行'}
            </button>
          </div>
        )}

        {/* Create/Edit Form */}
          {(showCreateForm || editingReservation) && (
          <div className="form-container">
            <h3>{editingReservation ? '予約編集' : '新規予約'}</h3>
            <form onSubmit={editingReservation ? updateReservation : createReservation}>
              <div className="form-group">
                <label>ベンチ:</label>
                <select 
                  value={formData.bench_id} 
                  onChange={(e) => setFormData({...formData, bench_id: e.target.value})}
                  disabled={!!editingReservation}
                >
                  <option value="front">手前</option>
                  <option value="back">奥</option>
                </select>
              </div>

              <div className="form-group">
                <label>利用者名:</label>
                <input
                  type="text"
                  value={formData.user_name}
                  onChange={(e) => setFormData({...formData, user_name: e.target.value})}
                  required
                  placeholder="お名前を入力してください"
                />
              </div>

              <div className="form-group">
                <label>開始時刻:</label>
                <input
                  type="time"
                  value={formData.start_time}
                  onChange={(e) => setFormData({...formData, start_time: e.target.value})}
                  min="07:00"
                  max="22:00"
                  step="1800"
                  required
                />
                <small style={{color: '#666', fontSize: '0.8rem'}}>
                  利用可能時間: 7:00-22:00 (30分刻み)
                </small>
              </div>

              <div className="form-group">
                <label>終了時刻:</label>
                <input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({...formData, end_time: e.target.value})}
                  min="07:00"
                  max="22:00"
                  step="1800"
                  required
                />
                <small style={{color: '#666', fontSize: '0.8rem'}}>
                  利用可能時間: 7:00-22:00 (30分刻み)
                </small>
              </div>

              <div className="form-buttons">
                <button type="submit" disabled={loading}>
                  {editingReservation ? '更新' : '予約作成'}
                </button>
                
                {editingReservation && (
                  <button 
                    type="button" 
                    className="delete-form-button"
                    disabled={loading}
                    onClick={() => {
                      console.log('削除ボタンがクリックされました');
                      console.log('編集中の予約:', editingReservation);
                      
                      const handleDelete = async () => {
                        try {
                          // 詳細な確認ダイアログ
                          const userConfirmed = window.confirm(
                            `⚠️ 予約を削除してもよろしいですか？\n\n` +
                            `📝 利用者: ${editingReservation.user_name}\n` +
                            `⏰ 時間: ${new Date(editingReservation.start_time).toTimeString().substring(0,5)} - ${new Date(editingReservation.end_time).toTimeString().substring(0,5)}\n` +
                            `🏢 ベンチ: ${editingReservation.bench_id === 'front' ? '手前' : '奥'}\n\n` +
                            `❌ この操作は取り消せません。\n\n` +
                            `削除する場合は「OK」を押してください。`
                          );
                          
                          if (!userConfirmed) {
                            console.log('ユーザーが削除をキャンセルしました');
                            return;
                          }
                          
                          console.log('削除処理を開始します...');
                          console.log('削除対象ID:', editingReservation.id);
                          
                          setLoading(true);
                          setError('');
                          
                          // DELETE リクエスト送信
                          const response = await axios.delete(`${API}/reservations/${editingReservation.id}`);
                          console.log('✅ 削除成功:', response.data);
                          
                          // 状態をリセット
                          setEditingReservation(null);
                          setFormData({ bench_id: 'front', user_name: '', start_time: '', end_time: '' });
                          
                          // 予約リストを再読み込み
                          await loadReservations();
                          console.log('✅ 削除処理が完了しました');
                          
                        } catch (error) {
                          console.error('❌ 削除エラー:', error);
                          if (error.response) {
                            console.error('レスポンスエラー:', error.response.data);
                            console.error('ステータスコード:', error.response.status);
                          }
                          setError(`削除に失敗しました: ${error.response?.data?.detail || error.message}`);
                        } finally {
                          setLoading(false);
                        }
                      };
                      
                      handleDelete();
                    }}
                  >
                    {loading ? '削除中...' : '🗑️ 予約削除'}
                  </button>
                )}
                
                <button 
                  type="button" 
                  onClick={() => {
                    setShowCreateForm(false);
                    setEditingReservation(null);
                    setError('');
                  }}
                >
                  キャンセル
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Timetable View */}
        <div className="timetable-container">
          {loading && <div className="loading">読み込み中...</div>}
          
          <div className="timetable">
            {/* Header */}
            <div className="timetable-header">
              <div className="time-column-header">時刻</div>
              <div className="bench-column-header">手前</div>
              <div className="bench-column-header">奥</div>
            </div>

            {/* Time grid */}
            <div className="timetable-grid">
              {/* Time column */}
              <div className="time-column">
                {timeSlots.map((time, index) => (
                  <div key={time} className="time-slot">
                    {time}
                  </div>
                ))}
              </div>

              {/* Front bench column */}
              <div className="bench-column" data-bench="front">
                <div className="bench-timeline">
                  {reservations
                    .filter(r => r.bench_id === 'front')
                    .map((reservation, index) => {
                      const { top, height } = calculateBarProperties(reservation);
                      return (
                        <div
                          key={reservation.id}
                          className="reservation-bar"
                          style={{
                            top: `${top}px`,
                            height: `${height}px`,
                            backgroundColor: getReservationColor(index),
                            left: '2px',
                            right: '2px'
                          }}
                          onClick={() => startEdit(reservation)}
                          title={`クリックして編集: ${reservation.user_name} (${new Date(reservation.start_time).toTimeString().substring(0,5)} - ${new Date(reservation.end_time).toTimeString().substring(0,5)})`}
                        >
                          <div className="reservation-content">
                            <div className="reservation-user">{reservation.user_name}</div>
                            <div className="reservation-time">
                              {new Date(reservation.start_time).toTimeString().substring(0,5)} - {new Date(reservation.end_time).toTimeString().substring(0,5)}
                            </div>
                          </div>
                          <div className="edit-indicator">
                            編集
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Back bench column */}
              <div className="bench-column" data-bench="back">
                <div className="bench-timeline">
                  {reservations
                    .filter(r => r.bench_id === 'back')
                    .map((reservation, index) => {
                      const { top, height } = calculateBarProperties(reservation);
                      return (
                        <div
                          key={reservation.id}
                          className="reservation-bar"
                          style={{
                            top: `${top}px`,
                            height: `${height}px`,
                            backgroundColor: getReservationColor(index + 6),
                            left: '2px',
                            right: '2px'
                          }}
                          onClick={() => startEdit(reservation)}
                          title={`クリックして編集: ${reservation.user_name} (${new Date(reservation.start_time).toTimeString().substring(0,5)} - ${new Date(reservation.end_time).toTimeString().substring(0,5)})`}
                        >
                          <div className="reservation-content">
                            <div className="reservation-user">{reservation.user_name}</div>
                            <div className="reservation-time">
                              {new Date(reservation.start_time).toTimeString().substring(0,5)} - {new Date(reservation.end_time).toTimeString().substring(0,5)}
                            </div>
                          </div>
                          <div className="edit-indicator">
                            編集
                          </div>
                        </div>
                      );
                    })}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
