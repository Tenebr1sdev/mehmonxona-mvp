from datetime import date
from pydantic import BaseModel, Field, ConfigDict

class LoginIn(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool = True
    model_config = ConfigDict(from_attributes=True)

class GuestIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=5, max_length=40)
    email: str | None = None
class GuestOut(GuestIn):
    id: int
    model_config = ConfigDict(from_attributes=True)

class RoomTypeIn(BaseModel):
    name: str
    capacity: int = Field(ge=1, le=12)
    price_per_night: float = Field(gt=0)
class RoomTypeOut(RoomTypeIn):
    id: int
    model_config = ConfigDict(from_attributes=True)
class RoomIn(BaseModel):
    number: str = Field(min_length=1, max_length=20)
    room_type_id: int
    state: str = "active"
class RoomOut(BaseModel):
    id: int
    number: str
    room_type_id: int
    type_name: str
    capacity: int
    price_per_night: float
    state: str

class ReservationIn(BaseModel):
    guest_id: int | None = None
    guest_name: str | None = None
    phone: str | None = None
    email: str | None = None
    room_id: int
    arrival: date
    departure: date
    payment_status: str = "unpaid"
class ReservationStatusIn(BaseModel):
    status: str
class ReservationOut(BaseModel):
    id: int
    code: str
    guest_id: int
    guest_name: str
    phone: str
    room_id: int
    room_number: str
    room_type: str
    arrival: date
    departure: date
    status: str
    amount: float
    paid: float
    created_at: str
