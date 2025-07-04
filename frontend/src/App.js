import React, { useState, useEffect } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

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

  // Load reservations for selected date
  const loadReservations = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/reservations`, {
        params: { date: selectedDate }
      });
      setReservations(response.data);
    } catch (err) {
      setError('予約の読み込みに失敗しました');
      console.error('Error loading reservations:', err);
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
      setLoading(false);
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

  // Delete reservation
  const deleteReservation = async (id) => {
    if (!window.confirm('この予約を削除してもよろしいですか？')) return;
    
    try {
      setLoading(true);
      await axios.delete(`${API}/reservations/${id}`);
      await loadReservations();
    } catch (err) {
      setError('予約の削除に失敗しました');
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

  // Format time for display
  const formatTime = (timeString) => {
    const date = new Date(timeString);
    return date.toLocaleTimeString('ja-JP', { 
      hour: '2-digit', 
      minute: '2-digit', 
      hour12: false 
    });
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

  // Group reservations by bench
  const groupedReservations = reservations.reduce((acc, reservation) => {
    if (!acc[reservation.bench_id]) {
      acc[reservation.bench_id] = [];
    }
    acc[reservation.bench_id].push(reservation);
    return acc;
  }, {});

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>クリーンベンチ予約システム</h1>
          <p>実験室のクリーンベンチをオンラインで予約できます</p>
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

        {/* Create Reservation Button */}
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
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            {error}
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
                  required
                />
              </div>

              <div className="form-group">
                <label>終了時刻:</label>
                <input
                  type="time"
                  value={formData.end_time}
                  onChange={(e) => setFormData({...formData, end_time: e.target.value})}
                  required
                />
              </div>

              <div className="form-buttons">
                <button type="submit" disabled={loading}>
                  {editingReservation ? '更新' : '予約作成'}
                </button>
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

        {/* Reservations Timeline */}
        <div className="reservations-container">
          {loading && <div className="loading">読み込み中...</div>}
          
          {/* Front Bench */}
          <div className="bench-section">
            <h3>手前のベンチ</h3>
            <div className="reservations-list">
              {groupedReservations.front?.length > 0 ? (
                groupedReservations.front.map(reservation => (
                  <div key={reservation.id} className="reservation-item">
                    <div className="reservation-time">
                      {formatTime(reservation.start_time)} - {formatTime(reservation.end_time)}
                    </div>
                    <div className="reservation-user">
                      {reservation.user_name}
                    </div>
                    <div className="reservation-actions">
                      <button onClick={() => startEdit(reservation)} className="edit-button">
                        編集
                      </button>
                      <button onClick={() => deleteReservation(reservation.id)} className="delete-button">
                        削除
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-reservations">予約がありません</div>
              )}
            </div>
          </div>

          {/* Back Bench */}
          <div className="bench-section">
            <h3>奥のベンチ</h3>
            <div className="reservations-list">
              {groupedReservations.back?.length > 0 ? (
                groupedReservations.back.map(reservation => (
                  <div key={reservation.id} className="reservation-item">
                    <div className="reservation-time">
                      {formatTime(reservation.start_time)} - {formatTime(reservation.end_time)}
                    </div>
                    <div className="reservation-user">
                      {reservation.user_name}
                    </div>
                    <div className="reservation-actions">
                      <button onClick={() => startEdit(reservation)} className="edit-button">
                        編集
                      </button>
                      <button onClick={() => deleteReservation(reservation.id)} className="delete-button">
                        削除
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="no-reservations">予約がありません</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;