from datetime import date, timedelta
from tests.conftest import auth

def test_login_and_me(client):
    headers=auth(client)
    response=client.get("/api/auth/me",headers=headers)
    assert response.status_code==200
    assert response.json()["role"]=="receptionist"

def test_create_and_conflict_reservation(client):
    headers=auth(client)
    today=date.today()
    payload={"guest_name":"Test Guest","phone":"+998900000000","room_id":1,"arrival":today.isoformat(),"departure":(today+timedelta(days=2)).isoformat(),"payment_status":"unpaid"}
    first=client.post("/api/reservations",json=payload,headers=headers)
    assert first.status_code==200
    assert first.json()["room_number"]=="T-01"
    second=client.post("/api/reservations",json={**payload,"guest_name":"Other Guest"},headers=headers)
    assert second.status_code==409

def test_role_protection(client):
    headers=auth(client)
    response=client.post("/api/users",json={"username":"new","password":"Password123!","role":"manager"},headers=headers)
    assert response.status_code==403

def test_health_and_summary(client):
    assert client.get("/api/health").json()["status"]=="ok"
    headers=auth(client)
    response=client.get("/api/analytics/summary",headers=headers)
    assert response.status_code==200
    assert response.json()["rooms_total"]==1
