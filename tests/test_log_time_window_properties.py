"""
Property-Based Tests for Log Time Window Calculation

Feature: incident-response-system
Property 4: Log Time Window Calculation

For any failure timestamp, the Log Analysis Agent should retrieve logs
from exactly 15 minutes before to 5 minutes after the timestamp.

Validates: Requirements 2.2
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime, timedelta, timezone
from src.agents.log_retrieval import calculate_time_window


@given(
    year=st.integers(min_value=2020, max_value=2030),
    month=st.integers(min_value=1, max_value=12),
    day=st.integers(min_value=1, max_value=28),  # Safe for all months
    hour=st.integers(min_value=0, max_value=23),
    minute=st.integers(min_value=0, max_value=59),
    second=st.integers(min_value=0, max_value=59)
)
@pytest.mark.property_test
def test_property_4_log_time_window_calculation(year, month, day, hour, minute, second):
    """
    Property 4: Log Time Window Calculation
    
    For any failure timestamp, the Log Analysis Agent should retrieve logs
    from exactly 15 minutes before to 5 minutes after the timestamp.
    
    Validates: Requirements 2.2
    """
    # Create a valid timestamp (timezone-aware)
    failure_time = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    timestamp_str = failure_time.isoformat().replace('+00:00', 'Z')
    
    # Calculate time window
    start_time, end_time = calculate_time_window(timestamp_str)
    
    # Property 1: Start time should be exactly 15 minutes before failure
    expected_start = failure_time - timedelta(minutes=15)
    assert start_time == expected_start, \
        f"Start time should be 15 minutes before failure. Expected: {expected_start}, Got: {start_time}"
    
    # Property 2: End time should be exactly 5 minutes after failure
    expected_end = failure_time + timedelta(minutes=5)
    assert end_time == expected_end, \
        f"End time should be 5 minutes after failure. Expected: {expected_end}, Got: {end_time}"
    
    # Property 3: Time window should be exactly 20 minutes
    window_duration = end_time - start_time
    expected_duration = timedelta(minutes=20)
    assert window_duration == expected_duration, \
        f"Time window should be exactly 20 minutes. Got: {window_duration}"
    
    # Property 4: Failure time should be within the window
    assert start_time <= failure_time <= end_time, \
        "Failure time should be within the calculated time window"


@given(timestamp=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31), timezones=st.just(timezone.utc)))
@pytest.mark.property_test
def test_property_4_time_window_with_datetime_strategy(timestamp):
    """
    Property 4: Log Time Window Calculation (using datetime strategy)
    
    Alternative test using hypothesis datetime strategy for more comprehensive coverage.
    
    Validates: Requirements 2.2
    """
    timestamp_str = timestamp.isoformat().replace('+00:00', 'Z')
    
    # Calculate time window
    start_time, end_time = calculate_time_window(timestamp_str)
    
    # Verify the window is correct
    expected_start = timestamp - timedelta(minutes=15)
    expected_end = timestamp + timedelta(minutes=5)
    
    assert start_time == expected_start
    assert end_time == expected_end
    assert (end_time - start_time) == timedelta(minutes=20)


@given(
    base_time=st.datetimes(min_value=datetime(2020, 1, 1), max_value=datetime(2030, 12, 31), timezones=st.just(timezone.utc)),
    offset_minutes=st.integers(min_value=-1000, max_value=1000)
)
@pytest.mark.property_test
def test_property_4_time_window_consistency(base_time, offset_minutes):
    """
    Property 4: Time window calculation should be consistent
    
    For any two timestamps that differ by a fixed amount, their time windows
    should also differ by the same amount.
    
    Validates: Requirements 2.2
    """
    # Create two timestamps with a known offset
    timestamp1 = base_time
    timestamp2 = base_time + timedelta(minutes=offset_minutes)
    
    timestamp1_str = timestamp1.isoformat().replace('+00:00', 'Z')
    timestamp2_str = timestamp2.isoformat().replace('+00:00', 'Z')
    
    # Calculate time windows
    start1, end1 = calculate_time_window(timestamp1_str)
    start2, end2 = calculate_time_window(timestamp2_str)
    
    # Property: The offset between windows should match the offset between timestamps
    start_offset = (start2 - start1).total_seconds() / 60  # Convert to minutes
    end_offset = (end2 - end1).total_seconds() / 60
    
    assert abs(start_offset - offset_minutes) < 0.01, \
        f"Start time offset should match timestamp offset. Expected: {offset_minutes}, Got: {start_offset}"
    assert abs(end_offset - offset_minutes) < 0.01, \
        f"End time offset should match timestamp offset. Expected: {offset_minutes}, Got: {end_offset}"
