#!/usr/bin/env python3
import requests
import json
import datetime
import pytz
from dateutil import parser
import time
import uuid
import sys
import os
from dotenv import load_dotenv

# Load the REACT_APP_BACKEND_URL from frontend/.env
load_dotenv('/app/frontend/.env')
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL')
BASE_URL = f"{BACKEND_URL}/api"

print(f"Using backend URL: {BASE_URL}")

# Japan Standard Time timezone
JST = pytz.timezone('Asia/Tokyo')

# Test results tracking
tests_passed = 0
tests_failed = 0
test_results = []

def print_test_result(test_name, passed, message=""):
    global tests_passed, tests_failed
    if passed:
        tests_passed += 1
        result = "✅ PASS"
    else:
        tests_failed += 1
        result = "❌ FAIL"
    
    test_results.append({
        "name": test_name,
        "result": "pass" if passed else "fail",
        "message": message
    })
    
    print(f"{result} - {test_name}")
    if message:
        print(f"       {message}")
    print()

def is_jst_timezone(time_str):
    """Check if a time string has JST timezone"""
    dt = parser.parse(time_str)
    # Check for JST timezone - could be represented as JST, +09:00, or Asia/Tokyo
    return dt.tzinfo is not None and (
        dt.tzinfo.tzname(dt) in ["JST", "+09:00"] or 
        "+09:00" in time_str or
        dt.utcoffset().total_seconds() == 9 * 3600  # 9 hours offset
    )

def get_current_jst_date():
    """Get current date in JST timezone in ISO format"""
    now = datetime.datetime.now(JST)
    return now.date().isoformat()

def generate_test_reservation(bench_id="front", hours_from_now=24, duration_minutes=60):
    """Generate test reservation data with times relative to now"""
    now = datetime.datetime.now(JST)
    # Use a time far in the future to avoid conflicts
    start_time = now + datetime.timedelta(hours=hours_from_now)
    end_time = start_time + datetime.timedelta(minutes=duration_minutes)
    
    return {
        "bench_id": bench_id,
        "user_name": f"テスト予約 {uuid.uuid4().hex[:8]}",
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat()
    }

# 1. Test API Health Check
def test_api_health():
    try:
        response = requests.get(f"{BASE_URL}/")
        data = response.json()
        
        is_success = (
            response.status_code == 200 and
            "message" in data and
            "current_time_jst" in data and
            is_jst_timezone(data["current_time_jst"])
        )
        
        message = f"Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("API Health Check", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("API Health Check", False, f"Exception: {str(e)}")
        return False

# 2. Test Bench Information
def test_bench_info():
    try:
        response = requests.get(f"{BASE_URL}/benches")
        data = response.json()
        
        is_success = (
            response.status_code == 200 and
            "benches" in data and
            len(data["benches"]) == 2 and
            any(bench["id"] == "front" and bench["name"] == "手前" for bench in data["benches"]) and
            any(bench["id"] == "back" and bench["name"] == "奥" for bench in data["benches"])
        )
        
        message = f"Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("Bench Information", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("Bench Information", False, f"Exception: {str(e)}")
        return False

# 3. Test Current Time
def test_current_time():
    try:
        response = requests.get(f"{BASE_URL}/current-time")
        data = response.json()
        
        is_success = (
            response.status_code == 200 and
            "current_time_jst" in data and
            is_jst_timezone(data["current_time_jst"])
        )
        
        message = f"Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("Current Time", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("Current Time", False, f"Exception: {str(e)}")
        return False

# 4. Test Create Reservation
def test_create_reservation():
    # Test front bench reservation
    front_reservation = generate_test_reservation("front", 30, 60)
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=front_reservation)
        data = response.json()
        
        front_success = (
            response.status_code == 200 and
            "id" in data and
            data["bench_id"] == front_reservation["bench_id"] and
            data["user_name"] == front_reservation["user_name"] and
            is_jst_timezone(data["start_time"]) and
            is_jst_timezone(data["end_time"])
        )
        
        front_message = f"Front bench - Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("Create Reservation (Front Bench)", front_success, front_message)
        
        # Store the reservation ID for later tests
        if front_success:
            front_id = data["id"]
        else:
            front_id = None
    except Exception as e:
        print_test_result("Create Reservation (Front Bench)", False, f"Exception: {str(e)}")
        front_success = False
        front_id = None
    
    # Test back bench reservation
    back_reservation = generate_test_reservation("back", 120, 60)
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=back_reservation)
        data = response.json()
        
        back_success = (
            response.status_code == 200 and
            "id" in data and
            data["bench_id"] == back_reservation["bench_id"] and
            data["user_name"] == back_reservation["user_name"] and
            is_jst_timezone(data["start_time"]) and
            is_jst_timezone(data["end_time"])
        )
        
        back_message = f"Back bench - Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("Create Reservation (Back Bench)", back_success, back_message)
        
        # Store the reservation ID for later tests
        if back_success:
            back_id = data["id"]
        else:
            back_id = None
    except Exception as e:
        print_test_result("Create Reservation (Back Bench)", False, f"Exception: {str(e)}")
        back_success = False
        back_id = None
    
    return front_success, back_success, front_id, back_id

# 5. Test JST Timezone Handling
def test_jst_timezone_handling(reservation_id):
    if not reservation_id:
        print_test_result("JST Timezone Handling", False, "No reservation ID available for testing")
        return False
    
    try:
        response = requests.get(f"{BASE_URL}/reservations/{reservation_id}")
        data = response.json()
        
        is_success = (
            response.status_code == 200 and
            is_jst_timezone(data["start_time"]) and
            is_jst_timezone(data["end_time"]) and
            is_jst_timezone(data["created_at"])
        )
        
        message = f"Status: {response.status_code}, Times: start={data['start_time']}, end={data['end_time']}, created={data['created_at']}"
        print_test_result("JST Timezone Handling", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("JST Timezone Handling", False, f"Exception: {str(e)}")
        return False

# 6. Test Double-booking Prevention
def test_double_booking_prevention(existing_reservation_id):
    if not existing_reservation_id:
        print_test_result("Double-booking Prevention", False, "No reservation ID available for testing")
        return False
    
    try:
        # Get the existing reservation details
        response = requests.get(f"{BASE_URL}/reservations/{existing_reservation_id}")
        existing = response.json()
        
        # Create an overlapping reservation
        overlapping = {
            "bench_id": existing["bench_id"],
            "user_name": f"重複予約 {uuid.uuid4().hex[:8]}",
            "start_time": existing["start_time"],  # Same start time
            "end_time": existing["end_time"]       # Same end time
        }
        
        response = requests.post(f"{BASE_URL}/reservations", json=overlapping)
        
        is_success = response.status_code == 409  # Conflict status code
        
        message = f"Status: {response.status_code}, Response: {response.text}"
        print_test_result("Double-booking Prevention", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("Double-booking Prevention", False, f"Exception: {str(e)}")
        return False

# 7. Test Get Reservations with Date Filtering
def test_get_reservations():
    try:
        # Get all reservations
        response = requests.get(f"{BASE_URL}/reservations")
        all_data = response.json()
        
        all_success = response.status_code == 200 and isinstance(all_data, list)
        all_message = f"All reservations - Status: {response.status_code}, Count: {len(all_data)}"
        print_test_result("Get All Reservations", all_success, all_message)
        
        # Get reservations for today
        today = get_current_jst_date()
        response = requests.get(f"{BASE_URL}/reservations?date={today}")
        today_data = response.json()
        
        today_success = response.status_code == 200 and isinstance(today_data, list)
        today_message = f"Today's reservations - Status: {response.status_code}, Count: {len(today_data)}"
        print_test_result("Get Today's Reservations", today_success, today_message)
        
        # Get reservations for front bench
        response = requests.get(f"{BASE_URL}/reservations?bench_id=front")
        front_data = response.json()
        
        front_success = (
            response.status_code == 200 and 
            isinstance(front_data, list) and
            all(r["bench_id"] == "front" for r in front_data)
        )
        front_message = f"Front bench reservations - Status: {response.status_code}, Count: {len(front_data)}"
        print_test_result("Get Front Bench Reservations", front_success, front_message)
        
        return all_success and today_success and front_success
    except Exception as e:
        print_test_result("Get Reservations", False, f"Exception: {str(e)}")
        return False

# 8. Test Update Reservation
def test_update_reservation(reservation_id):
    if not reservation_id:
        print_test_result("Update Reservation", False, "No reservation ID available for testing")
        return False
    
    try:
        # Get the existing reservation
        response = requests.get(f"{BASE_URL}/reservations/{reservation_id}")
        existing = response.json()
        
        # Create update data - extend the end time by 30 minutes
        end_time = parser.parse(existing["end_time"])
        new_end_time = end_time + datetime.timedelta(minutes=30)
        
        update_data = {
            "user_name": f"更新された予約 {uuid.uuid4().hex[:8]}",
            "end_time": new_end_time.isoformat()
        }
        
        # Update the reservation
        response = requests.put(f"{BASE_URL}/reservations/{reservation_id}", json=update_data)
        data = response.json()
        
        is_success = (
            response.status_code == 200 and
            data["id"] == reservation_id and
            data["user_name"] == update_data["user_name"] and
            parser.parse(data["end_time"]) > end_time
        )
        
        message = f"Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("Update Reservation", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("Update Reservation", False, f"Exception: {str(e)}")
        return False

# 9. Test Delete Reservation
def test_delete_reservation(reservation_id):
    if not reservation_id:
        print_test_result("Delete Reservation", False, "No reservation ID available for testing")
        return False
    
    try:
        # Delete the reservation
        response = requests.delete(f"{BASE_URL}/reservations/{reservation_id}")
        
        delete_success = response.status_code == 200
        delete_message = f"Delete - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Delete Reservation", delete_success, delete_message)
        
        # Verify it's gone
        verify_response = requests.get(f"{BASE_URL}/reservations/{reservation_id}")
        verify_success = verify_response.status_code == 404  # Not found
        verify_message = f"Verify deletion - Status: {verify_response.status_code}, Response: {verify_response.text}"
        print_test_result("Verify Reservation Deletion", verify_success, verify_message)
        
        return delete_success and verify_success
    except Exception as e:
        print_test_result("Delete Reservation", False, f"Exception: {str(e)}")
        return False

# 10. Test Edge Cases
def test_edge_cases():
    # Test invalid bench_id
    invalid_bench = generate_test_reservation()
    invalid_bench["bench_id"] = "invalid"
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=invalid_bench)
        invalid_bench_success = response.status_code == 422  # Validation error
        invalid_bench_message = f"Invalid bench_id - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Invalid Bench ID", invalid_bench_success, invalid_bench_message)
    except Exception as e:
        print_test_result("Invalid Bench ID", False, f"Exception: {str(e)}")
        invalid_bench_success = False
    
    # Test end time before start time
    invalid_time = generate_test_reservation()
    start = parser.parse(invalid_time["start_time"])
    end = start - datetime.timedelta(minutes=30)  # End before start
    invalid_time["end_time"] = end.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=invalid_time)
        invalid_time_success = response.status_code == 400  # Bad request
        invalid_time_message = f"End before start - Status: {response.status_code}, Response: {response.text}"
        print_test_result("End Time Before Start Time", invalid_time_success, invalid_time_message)
    except Exception as e:
        print_test_result("End Time Before Start Time", False, f"Exception: {str(e)}")
        invalid_time_success = False
    
    # Test missing required field
    missing_field = generate_test_reservation()
    del missing_field["user_name"]
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=missing_field)
        missing_field_success = response.status_code in [400, 422]  # Bad request or validation error
        missing_field_message = f"Missing user_name - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Missing Required Field", missing_field_success, missing_field_message)
    except Exception as e:
        print_test_result("Missing Required Field", False, f"Exception: {str(e)}")
        missing_field_success = False
    
    # Test malformed time format
    malformed_time = generate_test_reservation()
    malformed_time["start_time"] = "not-a-time"
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=malformed_time)
        malformed_time_success = response.status_code in [400, 422]  # Bad request or validation error
        malformed_time_message = f"Malformed time - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Malformed Time Format", malformed_time_success, malformed_time_message)
    except Exception as e:
        print_test_result("Malformed Time Format", False, f"Exception: {str(e)}")
        malformed_time_success = False
    
    # Test minute-level precision
    try:
        # Generate a reservation with specific minute values
        now = datetime.datetime.now(JST)
        # Use a time far in the future to avoid conflicts
        start = now + datetime.timedelta(hours=8)
        # Set specific minutes
        start = start.replace(minute=37, second=0, microsecond=0)
        end = start + datetime.timedelta(minutes=42)  # 42 minutes duration
        
        minute_precision = {
            "bench_id": "front",
            "user_name": f"分単位テスト {uuid.uuid4().hex[:8]}",
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }
        
        response = requests.post(f"{BASE_URL}/reservations", json=minute_precision)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if the returned times have the same minute values
            returned_start = parser.parse(data["start_time"])
            returned_end = parser.parse(data["end_time"])
            
            minute_precision_success = (
                returned_start.minute == start.minute and
                returned_end.minute == end.minute
            )
            
            minute_precision_message = f"Minute precision - Status: {response.status_code}, Start minute: {returned_start.minute}, End minute: {returned_end.minute}"
            
            # Clean up this test reservation
            if "id" in data:
                requests.delete(f"{BASE_URL}/reservations/{data['id']}")
        else:
            minute_precision_success = False
            minute_precision_message = f"Failed to create test reservation - Status: {response.status_code}, Response: {response.text}"
        
        print_test_result("Minute-level Precision", minute_precision_success, minute_precision_message)
    except Exception as e:
        print_test_result("Minute-level Precision", False, f"Exception: {str(e)}")
        minute_precision_success = False
    
    return (
        invalid_bench_success and 
        invalid_time_success and 
        missing_field_success and 
        malformed_time_success and 
        minute_precision_success
    )

# 11. Test Time Range Validation (7:00-22:00)
def test_time_range_validation():
    # Test reservation before 7:00
    before_hours = generate_test_reservation()
    start_dt = parser.parse(before_hours["start_time"])
    # Set to 6:30 AM
    before_start = start_dt.replace(hour=6, minute=30)
    before_end = before_start + datetime.timedelta(hours=1)
    before_hours["start_time"] = before_start.isoformat()
    before_hours["end_time"] = before_end.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=before_hours)
        before_hours_success = response.status_code == 400  # Should be rejected
        before_hours_message = f"Before 7:00 - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Reservation Before 7:00", before_hours_success, before_hours_message)
    except Exception as e:
        print_test_result("Reservation Before 7:00", False, f"Exception: {str(e)}")
        before_hours_success = False
    
    # Test reservation after 22:00
    after_hours = generate_test_reservation()
    start_dt = parser.parse(after_hours["start_time"])
    # Set to 22:30 PM
    after_start = start_dt.replace(hour=22, minute=30)
    after_end = after_start + datetime.timedelta(hours=1)
    after_hours["start_time"] = after_start.isoformat()
    after_hours["end_time"] = after_end.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=after_hours)
        after_hours_success = response.status_code == 400  # Should be rejected
        after_hours_message = f"After 22:00 - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Reservation After 22:00", after_hours_success, after_hours_message)
    except Exception as e:
        print_test_result("Reservation After 22:00", False, f"Exception: {str(e)}")
        after_hours_success = False
    
    # Test valid time range (7:00-22:00)
    valid_hours = generate_test_reservation()
    start_dt = parser.parse(valid_hours["start_time"])
    # Set to 9:00 AM
    valid_start = start_dt.replace(hour=9, minute=0)
    valid_end = valid_start + datetime.timedelta(hours=1)
    valid_hours["start_time"] = valid_start.isoformat()
    valid_hours["end_time"] = valid_end.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=valid_hours)
        valid_hours_success = response.status_code == 200  # Should be accepted
        valid_hours_message = f"Valid hours - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Valid Time Range (7:00-22:00)", valid_hours_success, valid_hours_message)
        
        # Clean up this test reservation
        if valid_hours_success and response.status_code == 200:
            data = response.json()
            if "id" in data:
                requests.delete(f"{BASE_URL}/reservations/{data['id']}")
    except Exception as e:
        print_test_result("Valid Time Range (7:00-22:00)", False, f"Exception: {str(e)}")
        valid_hours_success = False
    
    return before_hours_success and after_hours_success and valid_hours_success

# 12. Test 30-Minute Increments Validation
def test_30min_increments_validation():
    # Test non-30-minute increment start time
    invalid_start = generate_test_reservation()
    start_dt = parser.parse(invalid_start["start_time"])
    # Set to 10:15 (not on 30-min increment)
    invalid_start_time = start_dt.replace(hour=10, minute=15)
    invalid_end_time = invalid_start_time + datetime.timedelta(hours=1)
    invalid_start["start_time"] = invalid_start_time.isoformat()
    invalid_start["end_time"] = invalid_end_time.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=invalid_start)
        invalid_start_success = response.status_code == 400  # Should be rejected
        invalid_start_message = f"Invalid start time increment - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Non-30-Minute Start Time", invalid_start_success, invalid_start_message)
    except Exception as e:
        print_test_result("Non-30-Minute Start Time", False, f"Exception: {str(e)}")
        invalid_start_success = False
    
    # Test non-30-minute increment end time
    invalid_end = generate_test_reservation()
    start_dt = parser.parse(invalid_end["start_time"])
    # Set to valid start but invalid end
    valid_start_time = start_dt.replace(hour=10, minute=0)
    invalid_end_time = valid_start_time + datetime.timedelta(minutes=45)  # 10:45, not on 30-min increment
    invalid_end["start_time"] = valid_start_time.isoformat()
    invalid_end["end_time"] = invalid_end_time.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=invalid_end)
        invalid_end_success = response.status_code == 400  # Should be rejected
        invalid_end_message = f"Invalid end time increment - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Non-30-Minute End Time", invalid_end_success, invalid_end_message)
    except Exception as e:
        print_test_result("Non-30-Minute End Time", False, f"Exception: {str(e)}")
        invalid_end_success = False
    
    # Test valid 30-minute increments
    valid_increments = generate_test_reservation()
    start_dt = parser.parse(valid_increments["start_time"])
    # Set to 10:30 (valid 30-min increment)
    valid_start_time = start_dt.replace(hour=10, minute=30)
    valid_end_time = valid_start_time + datetime.timedelta(minutes=60)  # 11:30, valid 30-min increment
    valid_increments["start_time"] = valid_start_time.isoformat()
    valid_increments["end_time"] = valid_end_time.isoformat()
    
    try:
        response = requests.post(f"{BASE_URL}/reservations", json=valid_increments)
        valid_increments_success = response.status_code == 200  # Should be accepted
        valid_increments_message = f"Valid 30-min increments - Status: {response.status_code}, Response: {response.text}"
        print_test_result("Valid 30-Minute Increments", valid_increments_success, valid_increments_message)
        
        # Clean up this test reservation
        if valid_increments_success and response.status_code == 200:
            data = response.json()
            if "id" in data:
                requests.delete(f"{BASE_URL}/reservations/{data['id']}")
    except Exception as e:
        print_test_result("Valid 30-Minute Increments", False, f"Exception: {str(e)}")
        valid_increments_success = False
    
    return invalid_start_success and invalid_end_success and valid_increments_success

# 13. Test Database Connectivity
def test_database_connectivity():
    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()
        
        is_success = (
            response.status_code == 200 and
            "status" in data and
            data["status"] == "healthy" and
            "database" in data and
            data["database"] == "connected"
        )
        
        message = f"Status: {response.status_code}, Response: {json.dumps(data)}"
        print_test_result("Database Connectivity", is_success, message)
        return is_success
    except Exception as e:
        print_test_result("Database Connectivity", False, f"Exception: {str(e)}")
        return False

def run_all_tests():
    print("🧪 Starting Backend API Tests 🧪")
    print("=" * 50)
    print(f"Testing API at: {BASE_URL}")
    print("=" * 50)
    
    # Basic tests
    test_api_health()
    test_bench_info()
    test_current_time()
    
    # Reservation CRUD tests
    front_success, back_success, front_id, back_id = test_create_reservation()
    
    # Only continue with more tests if we have at least one valid reservation
    test_id = front_id or back_id
    if test_id:
        test_jst_timezone_handling(test_id)
        test_double_booking_prevention(test_id)
        test_get_reservations()
        test_update_reservation(test_id)
        
        # Use the other ID for delete test if available, otherwise use the same one
        delete_id = back_id if front_id and back_id else test_id
        test_delete_reservation(delete_id)
    
    # Edge cases
    test_edge_cases()
    
    # Print summary
    print("=" * 50)
    print(f"Test Summary: {tests_passed} passed, {tests_failed} failed")
    print("=" * 50)
    
    return tests_passed, tests_failed, test_results

if __name__ == "__main__":
    run_all_tests()