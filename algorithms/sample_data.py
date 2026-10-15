from typing import List
from algorithms.core_models import Priority, Stop, Vehicle


def get_sample_scenario() -> dict:
    """
    Returns realistic initial dataset for demonstration.
    Centered around Chengannur & central Kerala logistics route.
    """
    vehicle = Vehicle(id=1, capacity=80.0, speed_kmh=35.0)

    stops = [
        # Depot (ID 0)
        Stop(
            id=0,
            name="Central Logistics Depot, Chengannur",
            lat=9.3175,
            lng=76.6174,
            demand=0.0,
            time_window=(0.0, 480.0),
            service_time=0.0,
            priority=Priority.NORMAL,
            is_depot=True,
        ),
        # Stop 1: Critical medical supplies
        Stop(
            id=1,
            name="Taluk Hospital Medical Store",
            lat=9.3240,
            lng=76.6210,
            demand=15.0,
            time_window=(15.0, 90.0),
            service_time=12.0,
            priority=Priority.CRITICAL,
        ),
        # Stop 2: High priority pharmacy
        Stop(
            id=2,
            name="Kozhencherry Life Care Pharmacy",
            lat=9.3402,
            lng=76.6998,
            demand=25.0,
            time_window=(30.0, 160.0),
            service_time=15.0,
            priority=Priority.HIGH,
        ),
        # Stop 3: Normal retail
        Stop(
            id=3,
            name="Pandalam Central Mart",
            lat=9.2312,
            lng=76.6806,
            demand=30.0,
            time_window=(60.0, 240.0),
            service_time=10.0,
            priority=Priority.NORMAL,
        ),
        # Stop 4: Normal retail
        Stop(
            id=4,
            name="Thiruvalla Commercial Hub",
            lat=9.3842,
            lng=76.5750,
            demand=35.0,
            time_window=(60.0, 300.0),
            service_time=15.0,
            priority=Priority.NORMAL,
        ),
        # Stop 5: Critical blood bank delivery
        Stop(
            id=5,
            name="Mavelikara District Clinic",
            lat=9.2678,
            lng=76.5450,
            demand=15.0,
            time_window=(20.0, 110.0),
            service_time=10.0,
            priority=Priority.CRITICAL,
        ),
        # Stop 6: Low priority hardware
        Stop(
            id=6,
            name="Haripad Hardware & Supplies",
            lat=9.2850,
            lng=76.4520,
            demand=20.0,
            time_window=(90.0, 380.0),
            service_time=15.0,
            priority=Priority.LOW,
        ),
        # Stop 7: Normal warehouse
        Stop(
            id=7,
            name="Aranmula Heritage Craft Outlet",
            lat=9.3330,
            lng=76.6840,
            demand=25.0,
            time_window=(80.0, 320.0),
            service_time=10.0,
            priority=Priority.LOW,
        ),
        # Stop 8: High priority clinic
        Stop(
            id=8,
            name="Adoor Healthcare Center",
            lat=9.1530,
            lng=76.7340,
            demand=20.0,
            time_window=(45.0, 180.0),
            service_time=15.0,
            priority=Priority.HIGH,
        ),
    ]

    return {
        "vehicle": vehicle,
        "stops": stops,
    }
