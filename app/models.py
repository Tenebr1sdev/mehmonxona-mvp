from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="receptionist")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class Guest(Base):
    __tablename__ = "guests"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160), index=True)
    phone: Mapped[str] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, unique=True)
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="guest")

class RoomType(Base):
    __tablename__ = "room_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    capacity: Mapped[int] = mapped_column(Integer)
    price_per_night: Mapped[float] = mapped_column(Float)
    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")

class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"))
    state: Mapped[str] = mapped_column(String(30), default="active")
    room_type: Mapped[RoomType] = relationship(back_populates="rooms")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="room")

class Reservation(Base):
    __tablename__ = "reservations"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    guest_id: Mapped[int] = mapped_column(ForeignKey("guests.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    arrival: Mapped[date] = mapped_column(Date)
    departure: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="confirmed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    guest: Mapped[Guest] = relationship(back_populates="reservations")
    room: Mapped[Room] = relationship(back_populates="reservations")
    payments: Mapped[list["Payment"]] = relationship(back_populates="reservation", cascade="all, delete-orphan")
    services: Mapped[list["ReservationService"]] = relationship(back_populates="reservation", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), index=True)
    amount: Mapped[float] = mapped_column(Float)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(30), default="paid")
    reservation: Mapped[Reservation] = relationship(back_populates="payments")

class Service(Base):
    __tablename__ = "services"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    price: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reservations: Mapped[list["ReservationService"]] = relationship(back_populates="service")

class ReservationService(Base):
    __tablename__ = "reservation_services"
    id: Mapped[int] = mapped_column(primary_key=True)
    reservation_id: Mapped[int] = mapped_column(ForeignKey("reservations.id"), index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    reservation: Mapped[Reservation] = relationship(back_populates="services")
    service: Mapped[Service] = relationship(back_populates="reservations")

class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    id: Mapped[int] = mapped_column(primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
