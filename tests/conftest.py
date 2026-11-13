import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./unused-test.db")
os.environ.setdefault("SECRET_KEY", "test-only-secret-key")
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import User, RoomType, Room
from app.security import hash_password

@pytest.fixture()
def client():
    engine=create_engine("sqlite://", connect_args={"check_same_thread":False}, poolclass=StaticPool)
    TestingSession=sessionmaker(bind=engine,autoflush=False,autocommit=False)
    Base.metadata.create_all(engine)
    db=TestingSession()
    db.add_all([
      User(id=1,username="test-admin",full_name="Test Admin",role="administrator",password_hash=hash_password("TestPassword123!")),
      User(id=2,username="test-reception",full_name="Test Reception",role="receptionist",password_hash=hash_password("TestPassword123!")),
      RoomType(id=1,name="Standart",capacity=2,price_per_night=100000),
    ]);db.commit();db.add(Room(id=1,number="T-01",room_type_id=1,state="active"));db.commit();db.close()
    def override_db():
        session=TestingSession()
        try:yield session
        finally:session.close()
    app.dependency_overrides[get_db]=override_db
    with TestClient(app) as tc:yield tc
    app.dependency_overrides.clear();Base.metadata.drop_all(engine);engine.dispose()

def auth(client,username="test-reception"):
    r=client.post("/api/auth/login",data={"username":username,"password":"TestPassword123!"})
    assert r.status_code==200
    return {"Authorization":"Bearer "+r.json()["access_token"]}
