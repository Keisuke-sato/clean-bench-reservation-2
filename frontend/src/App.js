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
    try {
      // 確認ダイアログを表示
      const confirmed = window.confirm('この予約を削除してもよろしいですか？\nこの操作は取り消せません。');
      if (!confirmed) return;
      
      setLoading(true);
      setError(''); // エラーをクリア
      
      const response = await axios.delete(`${API}/reservations/${id}`);
      
      // 削除成功
      await loadReservations();
      
      // 成功メッセージは一時的に表示（オプション）
      console.log('予約が正常に削除されました');
      
    } catch (err) {
      console.error('Delete error:', err);
      setError(err.response?.data?.detail || '予約の削除に失敗しました');
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

  // Generate time slots for timetable (every 15 minutes for performance)
  const generateTimeSlots = () => {
    const slots = [];
    for (let hour = 0; hour < 24; hour++) {
      for (let minute = 0; minute < 60; minute += 15) {
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
    
    // Each 15-minute slot is 40px high
    const pixelsPerMinute = 40 / 15;
    const top = startMinutes * pixelsPerMinute;
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

  const timeSlots = generateTimeSlots();

  return (
    <div className="app">
      <div className="container">
        <header className="header">
          <h1>クリーンベンチ予約システム</h1>
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
                          title={`${reservation.user_name} (${new Date(reservation.start_time).toTimeString().substring(0,5)} - ${new Date(reservation.end_time).toTimeString().substring(0,5)})`}
                        >
                          <div className="reservation-content">
                            <div className="reservation-user">{reservation.user_name}</div>
                            <div className="reservation-time">
                              {new Date(reservation.start_time).toTimeString().substring(0,5)} - {new Date(reservation.end_time).toTimeString().substring(0,5)}
                            </div>
                          </div>
                          <div className="reservation-actions">
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                startEdit(reservation);
                              }}
                              className="edit-button"
                              title="この予約を編集"
                            >
                              編集
                            </button>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteReservation(reservation.id);
                              }}
                              className="delete-button"
                              title="この予約を削除"
                            >
                              削除
                            </button>
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
                          title={`${reservation.user_name} (${new Date(reservation.start_time).toTimeString().substring(0,5)} - ${new Date(reservation.end_time).toTimeString().substring(0,5)})`}
                        >
                          <div className="reservation-content">
                            <div className="reservation-user">{reservation.user_name}</div>
                            <div className="reservation-time">
                              {new Date(reservation.start_time).toTimeString().substring(0,5)} - {new Date(reservation.end_time).toTimeString().substring(0,5)}
                            </div>
                          </div>
                          <div className="reservation-actions">
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                startEdit(reservation);
                              }}
                              className="edit-button"
                              title="この予約を編集"
                            >
                              編集
                            </button>
                            <button 
                              onClick={(e) => {
                                e.stopPropagation();
                                deleteReservation(reservation.id);
                              }}
                              className="delete-button"
                              title="この予約を削除"
                            >
                              削除
                            </button>
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