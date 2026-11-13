from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
import logging, shutil
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.config import settings
from app.database import get_db
from app.models import User, Guest, RoomType, Room, Reservation, Payment, Service, ReservationService, UploadedFile
from app.schemas import LoginIn, UserOut, GuestIn, GuestOut, RoomIn, RoomOut, RoomTypeIn, RoomTypeOut, ReservationIn, ReservationStatusIn
from app.security import current_user, require_roles, verify_password, create_token, hash_password
from app import ml

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("hotel")
app = FastAPI(title="Mehmonxona boshqaruvi API", version="1.0.0", description="Bron, xona, mehmon, to'lov, fayl, tahlil va o'quv ML API.")
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    log.exception("Kutilmagan server xatosi: %s %s", request.method, request.url.path)
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=500, content={"detail":"Ichki server xatosi"})

@app.get("/api/health", tags=["Tizim"])
def health(): return {"status":"ok", "service":"mehmonxona-mvp"}

@app.post("/api/auth/login", tags=["Kirish"])
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Login yoki parol noto‘g‘ri")
    if not user.is_active: raise HTTPException(403, "Foydalanuvchi faol emas")
    return {"access_token":create_token(user), "token_type":"bearer", "user":UserOut.model_validate(user).model_dump()}

@app.get("/api/auth/me", response_model=UserOut, tags=["Kirish"])
def me(user: User = Depends(current_user)): return user

@app.get("/api/users", tags=["Foydalanuvchilar"])
def list_users(db: Session=Depends(get_db), _:User=Depends(require_roles("administrator"))):
    return [UserOut.model_validate(x) for x in db.query(User).order_by(User.id).all()]

@app.post("/api/users", tags=["Foydalanuvchilar"])
def create_user(data: dict, db:Session=Depends(get_db), _:User=Depends(require_roles("administrator"))):
    role=data.get("role")
    if role not in {"administrator","manager","receptionist","guest"}: raise HTTPException(400,"Rol noto‘g‘ri")
    if not data.get("username") or not data.get("password") or len(data["password"])<8: raise HTTPException(400,"Login va kamida 8 belgili parol kiriting")
    if db.query(User).filter_by(username=data["username"]).first(): raise HTTPException(409,"Bu login mavjud")
    full_name=data.get("full_name",data["username"])
    u=User(username=data["username"],full_name=full_name,role=role,password_hash=hash_password(data["password"]))
    db.add(u);db.flush()
    if role=="guest":
        db.add(Guest(full_name=full_name,phone="Noma'lum",email=data["username"],user_id=u.id))
    db.commit();db.refresh(u);return UserOut.model_validate(u)

@app.patch("/api/guests/{guest_id}", response_model=GuestOut, tags=["Mehmonlar"])
def update_guest(guest_id:int,data:dict,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    guest=db.get(Guest,guest_id)
    if not guest:raise HTTPException(404,"Mehmon topilmadi")
    for key in ("full_name","phone","email"):
        if key in data:setattr(guest,key,data[key])
    db.commit();db.refresh(guest);return guest
@app.delete("/api/guests/{guest_id}",tags=["Mehmonlar"])
def delete_guest(guest_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    guest=db.get(Guest,guest_id)
    if not guest:raise HTTPException(404,"Mehmon topilmadi")
    if db.query(Reservation).filter_by(guest_id=guest_id).first():raise HTTPException(409,"Mehmonning bronlari bor; avval bronlarni boshqaring")
    db.delete(guest);db.commit();return {"deleted":guest_id}

@app.get("/api/services",tags=["Xizmatlar"])
def list_services(db:Session=Depends(get_db),_:User=Depends(current_user)):
    return [{"id":x.id,"name":x.name,"price":x.price,"is_active":x.is_active} for x in db.query(Service).order_by(Service.name).all()]
@app.post("/api/services",tags=["Xizmatlar"])
def create_service(data:dict,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    if not data.get("name") or float(data.get("price",0))<=0:raise HTTPException(400,"Xizmat nomi va musbat narx kiriting")
    obj=Service(name=data["name"],price=float(data["price"]));db.add(obj);db.commit();db.refresh(obj);return {"id":obj.id,"name":obj.name,"price":obj.price,"is_active":obj.is_active}
@app.patch("/api/services/{service_id}",tags=["Xizmatlar"])
def update_service(service_id:int,data:dict,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    obj=db.get(Service,service_id)
    if not obj:raise HTTPException(404,"Xizmat topilmadi")
    if "name" in data:obj.name=data["name"]
    if "price" in data:
        if float(data["price"])<=0:raise HTTPException(400,"Narx musbat bo‘lishi kerak")
        obj.price=float(data["price"])
    if "is_active" in data:obj.is_active=bool(data["is_active"])
    db.commit();return {"id":obj.id,"name":obj.name,"price":obj.price,"is_active":obj.is_active}
@app.delete("/api/services/{service_id}",tags=["Xizmatlar"])
def delete_service(service_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator"))):
    obj=db.get(Service,service_id)
    if not obj:raise HTTPException(404,"Xizmat topilmadi")
    if db.query(ReservationService).filter_by(service_id=service_id).first():raise HTTPException(409,"Xizmat bronlarda ishlatilgan")
    db.delete(obj);db.commit();return {"deleted":service_id}

@app.get("/api/room-types", response_model=list[RoomTypeOut], tags=["Xonalar"])
def room_types(db:Session=Depends(get_db), _:User=Depends(current_user)):
    return db.query(RoomType).order_by(RoomType.price_per_night).all()
@app.post("/api/room-types", response_model=RoomTypeOut, tags=["Xonalar"])
def create_room_type(data:RoomTypeIn,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    if db.query(RoomType).filter_by(name=data.name).first(): raise HTTPException(409,"Xona turi mavjud")
    obj=RoomType(**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return obj

@app.get("/api/rooms", response_model=list[RoomOut], tags=["Xonalar"])
def rooms(db:Session=Depends(get_db), _:User=Depends(current_user)):
    return [{"id":r.id,"number":r.number,"room_type_id":r.room_type_id,"type_name":r.room_type.name,"capacity":r.room_type.capacity,"price_per_night":r.room_type.price_per_night,"state":r.state} for r in db.query(Room).options(joinedload(Room.room_type)).order_by(Room.number).all()]
@app.put("/api/room-types/{type_id}", response_model=RoomTypeOut, tags=["Xonalar"])
def update_room_type(type_id:int,data:RoomTypeIn,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    obj=db.get(RoomType,type_id)
    if not obj:raise HTTPException(404,"Xona turi topilmadi")
    for key,value in data.model_dump().items():setattr(obj,key,value)
    db.commit();db.refresh(obj);return obj
@app.delete("/api/room-types/{type_id}",tags=["Xonalar"])
def delete_room_type(type_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator"))):
    obj=db.get(RoomType,type_id)
    if not obj:raise HTTPException(404,"Xona turi topilmadi")
    if obj.rooms:raise HTTPException(409,"Bu turga tegishli xonalar mavjud")
    db.delete(obj);db.commit();return {"deleted":type_id}

@app.post("/api/rooms", response_model=RoomOut, tags=["Xonalar"])
def create_room(data:RoomIn,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    if data.state not in {"active","maintenance"}: raise HTTPException(400,"Xona holati noto‘g‘ri")
    if not db.get(RoomType,data.room_type_id): raise HTTPException(404,"Xona turi topilmadi")
    obj=Room(**data.model_dump());db.add(obj)
    try: db.commit()
    except Exception: db.rollback();raise HTTPException(409,"Xona raqami band")
    db.refresh(obj);return {"id":obj.id,"number":obj.number,"room_type_id":obj.room_type_id,"type_name":obj.room_type.name,"capacity":obj.room_type.capacity,"price_per_night":obj.room_type.price_per_night,"state":obj.state}
@app.patch("/api/rooms/{room_id}", tags=["Xonalar"])
def update_room(room_id:int,data:dict,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    obj=db.get(Room,room_id)
    if not obj: raise HTTPException(404,"Xona topilmadi")
    if "state" in data:
        if data["state"] not in {"active","maintenance"}:raise HTTPException(400,"Holat noto‘g‘ri")
        obj.state=data["state"]
    db.commit();return {"id":obj.id,"state":obj.state}

@app.delete("/api/rooms/{room_id}",tags=["Xonalar"])
def delete_room(room_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    room=db.get(Room,room_id)
    if not room:raise HTTPException(404,"Xona topilmadi")
    if db.query(Reservation).filter_by(room_id=room_id).first():raise HTTPException(409,"Xonaga tegishli bronlar bor")
    db.delete(room);db.commit();return {"deleted":room_id}

@app.get("/api/guests", response_model=list[GuestOut], tags=["Mehmonlar"])
def guests(q:str|None=None,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    query=db.query(Guest)
    if q: query=query.filter(Guest.full_name.ilike(f"%{q}%"))
    return query.order_by(Guest.full_name).limit(200).all()
@app.post("/api/guests", response_model=GuestOut, tags=["Mehmonlar"])
def create_guest(data:GuestIn,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    obj=Guest(**data.model_dump());db.add(obj);db.commit();db.refresh(obj);return obj

@app.get("/api/my-reservations", tags=["Mehmonlar"])
def my_reservations(db:Session=Depends(get_db),user:User=Depends(require_roles("guest"))):
    guest=db.query(Guest).filter(Guest.user_id==user.id).first()
    if not guest:return []
    rows=db.query(Reservation).options(joinedload(Reservation.guest),joinedload(Reservation.room).joinedload(Room.room_type),joinedload(Reservation.payments)).filter(Reservation.guest_id==guest.id).order_by(Reservation.created_at.desc()).all()
    return [reservation_dict(x) for x in rows]

@app.post("/api/my-reservations", tags=["Mehmonlar"])
def guest_reservation(data:dict,db:Session=Depends(get_db),user:User=Depends(require_roles("guest"))):
    guest=db.query(Guest).filter(Guest.user_id==user.id).first()
    if not guest:raise HTTPException(404,"Sizning mehmon profilingiz topilmadi. Qabulxonaga murojaat qiling.")
    try:room_id=int(data.get("room_id"));arrival=date.fromisoformat(data.get("arrival",""));departure=date.fromisoformat(data.get("departure",""))
    except (ValueError,TypeError):raise HTTPException(400,"Xona va sanalarni to‘g‘ri kiriting")
    if departure<=arrival:raise HTTPException(400,"Ketish sanasi kelish sanasidan keyin bo‘lishi kerak")
    room=check_room(db,room_id,arrival,departure)
    obj=Reservation(code=f"H{uuid4().hex[:8].upper()}",guest_id=guest.id,room_id=room.id,arrival=arrival,departure=departure,status="confirmed")
    db.add(obj);db.commit();return {"code":obj.code,"status":obj.status}

@app.get("/api/reservations", tags=["Bronlar"])
def reservations(status:str|None=None,q:str|None=None,arrival_from:date|None=None,arrival_to:date|None=None,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    query=db.query(Reservation).options(joinedload(Reservation.guest),joinedload(Reservation.room).joinedload(Room.room_type),joinedload(Reservation.payments))
    if status and status!="all":query=query.filter(Reservation.status==status)
    if arrival_from:query=query.filter(Reservation.arrival>=arrival_from)
    if arrival_to:query=query.filter(Reservation.arrival<=arrival_to)
    if q:query=query.join(Guest).filter(Guest.full_name.ilike(f"%{q}%"))
    return [reservation_dict(x) for x in query.order_by(Reservation.created_at.desc()).limit(500).all()]

def reservation_dict(r):
    total=max((r.departure-r.arrival).days,0)*r.room.room_type.price_per_night
    paid=sum(p.amount for p in r.payments if p.status=="paid")
    return {"id":r.id,"code":r.code,"guest_id":r.guest_id,"guest_name":r.guest.full_name,"phone":r.guest.phone,"room_id":r.room_id,"room_number":r.room.number,"room_type":r.room.room_type.name,"arrival":r.arrival.isoformat(),"departure":r.departure.isoformat(),"status":r.status,"amount":total,"paid":paid,"created_at":r.created_at.isoformat()}

def check_room(db,room_id,arrival,departure,exclude=None):
    room=db.get(Room,room_id)
    if not room or room.state!="active":raise HTTPException(400,"Xona topilmadi yoki foydalanish uchun yopiq")
    query=db.query(Reservation).filter(Reservation.room_id==room_id,Reservation.status.in_(["confirmed","staying"]),Reservation.arrival<departure,Reservation.departure>arrival)
    if exclude:query=query.filter(Reservation.id!=exclude)
    if query.first():raise HTTPException(409,"Tanlangan sanalarda xona band")
    return room

@app.post("/api/reservations", tags=["Bronlar"])
def create_reservation(data:ReservationIn,db:Session=Depends(get_db),user:User=Depends(require_roles("administrator","manager","receptionist"))):
    if data.departure<=data.arrival:raise HTTPException(400,"Ketish sanasi kelish sanasidan keyin bo‘lishi kerak")
    room=check_room(db,data.room_id,data.arrival,data.departure)
    if data.guest_id: guest=db.get(Guest,data.guest_id)
    elif data.guest_name and data.phone:
        guest=Guest(full_name=data.guest_name,phone=data.phone,email=data.email);db.add(guest);db.flush()
    else:raise HTTPException(400,"Mehmonni tanlang yoki ism va telefonini kiriting")
    if not guest:raise HTTPException(404,"Mehmon topilmadi")
    obj=Reservation(code=f"H{uuid4().hex[:8].upper()}",guest_id=guest.id,room_id=room.id,arrival=data.arrival,departure=data.departure,status="staying" if data.arrival<=date.today()<data.departure else "confirmed")
    db.add(obj);db.flush();amount=(data.departure-data.arrival).days*room.room_type.price_per_night
    if data.payment_status=="paid":db.add(Payment(reservation_id=obj.id,amount=amount,status="paid"))
    elif data.payment_status=="partial":db.add(Payment(reservation_id=obj.id,amount=amount/2,status="paid"))
    db.commit();db.refresh(obj);return reservation_dict(db.query(Reservation).options(joinedload(Reservation.guest),joinedload(Reservation.room).joinedload(Room.room_type),joinedload(Reservation.payments)).get(obj.id))
@app.patch("/api/reservations/{reservation_id}/status",tags=["Bronlar"])
def update_reservation(reservation_id:int,data:ReservationStatusIn,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    if data.status not in {"confirmed","staying","done","cancelled"}:raise HTTPException(400,"Bron holati noto‘g‘ri")
    obj=db.get(Reservation,reservation_id)
    if not obj:raise HTTPException(404,"Bron topilmadi")
    if data.status in {"confirmed","staying"}:check_room(db,obj.room_id,obj.arrival,obj.departure,exclude=obj.id)
    obj.status=data.status;db.commit();return {"id":obj.id,"status":obj.status}
@app.delete("/api/reservations/{reservation_id}",tags=["Bronlar"])
def delete_reservation(reservation_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    obj=db.get(Reservation,reservation_id)
    if not obj:raise HTTPException(404,"Bron topilmadi")
    db.delete(obj);db.commit();return {"deleted":reservation_id}

@app.post("/api/reservations/{reservation_id}/payments",tags=["To‘lovlar"])
def add_payment(reservation_id:int,data:dict,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    r=db.get(Reservation,reservation_id)
    if not r:raise HTTPException(404,"Bron topilmadi")
    amount=float(data.get("amount",0))
    if amount<=0:raise HTTPException(400,"To‘lov summasi musbat bo‘lishi kerak")
    p=Payment(reservation_id=r.id,amount=amount,status="paid");db.add(p);db.commit();return {"id":p.id,"amount":p.amount,"status":p.status}

@app.get("/api/reservations/{reservation_id}/payments",tags=["To‘lovlar"])
def list_payments(reservation_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    if not db.get(Reservation,reservation_id):raise HTTPException(404,"Bron topilmadi")
    return [{"id":p.id,"amount":p.amount,"status":p.status,"paid_at":p.paid_at.isoformat()} for p in db.query(Payment).filter_by(reservation_id=reservation_id).order_by(Payment.paid_at.desc()).all()]
@app.delete("/api/payments/{payment_id}",tags=["To‘lovlar"])
def delete_payment(payment_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    item=db.get(Payment,payment_id)
    if not item:raise HTTPException(404,"To‘lov topilmadi")
    db.delete(item);db.commit();return {"deleted":payment_id}
@app.post("/api/reservations/{reservation_id}/services",tags=["Xizmatlar"])
def add_reservation_service(reservation_id:int,data:dict,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    if not db.get(Reservation,reservation_id):raise HTTPException(404,"Bron topilmadi")
    service=db.get(Service,int(data.get("service_id",0)));quantity=int(data.get("quantity",1))
    if not service or not service.is_active:raise HTTPException(404,"Faol xizmat topilmadi")
    if quantity<1:raise HTTPException(400,"Miqdor kamida 1 bo‘lishi kerak")
    item=ReservationService(reservation_id=reservation_id,service_id=service.id,quantity=quantity);db.add(item);db.commit();return {"id":item.id,"service":service.name,"quantity":quantity,"total":service.price*quantity}

ALLOWED={"text/csv","application/vnd.ms-excel","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","application/pdf","image/jpeg","image/png","image/webp"}
@app.post("/api/files",tags=["Fayllar"])
async def upload_file(file:UploadFile=File(...),db:Session=Depends(get_db),user:User=Depends(require_roles("administrator","manager","receptionist"))):
    if file.content_type not in ALLOWED:raise HTTPException(415,"Faqat CSV, Excel, PDF yoki rasm fayllari qabul qilinadi")
    folder=Path(settings.upload_dir);folder.mkdir(parents=True,exist_ok=True);stored=f"{uuid4().hex}_{Path(file.filename or 'file').name[:100]}";target=folder/stored;size=0
    with target.open("wb") as out:
        while chunk:=await file.read(1024*1024):
            size+=len(chunk)
            if size>settings.max_upload_mb*1024*1024:
                out.close();target.unlink(missing_ok=True);raise HTTPException(413,"Fayl hajmi 12 MB dan oshmasin")
            out.write(chunk)
    if settings.gcs_bucket:
        from google.cloud import storage
        storage.Client().bucket(settings.gcs_bucket).blob(stored).upload_from_filename(str(target), content_type=file.content_type)
        target.unlink(missing_ok=True)
    row=UploadedFile(original_name=Path(file.filename or 'file').name,stored_name=stored,content_type=file.content_type,size_bytes=size,uploaded_by=user.id);db.add(row);db.commit();db.refresh(row)
    return {"id":row.id,"name":row.original_name,"type":row.content_type,"size":row.size_bytes,"download_url":f"/api/files/{row.id}"}
@app.get("/api/files",tags=["Fayllar"])
def list_files(db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    return [{"id":f.id,"name":f.original_name,"type":f.content_type,"size":f.size_bytes,"created_at":f.created_at.isoformat()} for f in db.query(UploadedFile).order_by(UploadedFile.created_at.desc()).all()]
@app.get("/api/files/{file_id}",tags=["Fayllar"])
def download_file(file_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    f=db.get(UploadedFile,file_id)
    if not f:raise HTTPException(404,"Fayl topilmadi")
    path=Path(settings.upload_dir)/f.stored_name
    if settings.gcs_bucket:
        from google.cloud import storage
        blob=storage.Client().bucket(settings.gcs_bucket).blob(f.stored_name)
        if not blob.exists():raise HTTPException(404,"Fayl saqlash joyida topilmadi")
        return Response(blob.download_as_bytes(),media_type=f.content_type,headers={"Content-Disposition":f'attachment; filename="{f.original_name}"'})
    if not path.exists():raise HTTPException(404,"Fayl saqlash joyida topilmadi")
    return FileResponse(path,media_type=f.content_type,filename=f.original_name)

@app.delete("/api/files/{file_id}",tags=["Fayllar"])
def delete_file(file_id:int,db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    item=db.get(UploadedFile,file_id)
    if not item:raise HTTPException(404,"Fayl topilmadi")
    path=Path(settings.upload_dir)/item.stored_name
    if settings.gcs_bucket:
        from google.cloud import storage
        blob=storage.Client().bucket(settings.gcs_bucket).blob(item.stored_name)
        if blob.exists():blob.delete()
    else:path.unlink(missing_ok=True)
    db.delete(item);db.commit();return {"deleted":file_id}

@app.get("/api/analytics/summary",tags=["Tahlil"])
def summary(db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    total=db.query(Room).count();maint=db.query(Room).filter_by(state="maintenance").count();today=date.today();tomorrow=today+timedelta(days=1)
    occupied=db.query(Reservation.room_id).filter(Reservation.status.in_(["confirmed","staying"]),Reservation.arrival<tomorrow,Reservation.departure>today).distinct().count()
    active=db.query(Reservation).filter(Reservation.status.in_(["confirmed","staying"])).count()
    revenue=db.query(func.coalesce(func.sum(Payment.amount),0)).join(Reservation).filter(Payment.status=="paid",Reservation.status!="cancelled").scalar() or 0
    types=[]
    for typ in db.query(RoomType).all():
        ids=[r.id for r in db.query(Room).filter_by(room_type_id=typ.id,state="active").all()]
        count=db.query(Reservation.room_id).filter(Reservation.room_id.in_(ids or [-1]),Reservation.status.in_(["confirmed","staying"]),Reservation.arrival<tomorrow,Reservation.departure>today).distinct().count()
        types.append({"name":typ.name,"occupied":count,"total":len(ids)})
    return {"rooms_total":total,"rooms_maintenance":maint,"rooms_occupied":occupied,"rooms_free":max(total-maint-occupied,0),"occupancy_rate":round(occupied/max(total-maint,1)*100,1),"active_reservations":active,"revenue":float(revenue),"room_types":types}
@app.get("/api/analytics/series",tags=["Tahlil"])
def series(days:int=Query(7,ge=7,le=30),db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager","receptionist"))):
    start=date.today()-timedelta(days=days-1);rows=[]
    for i in range(days):
        d=start+timedelta(days=i);end=d+timedelta(days=1)
        occupied=db.query(Reservation.room_id).filter(Reservation.status.in_(["confirmed","staying"]),Reservation.arrival<end,Reservation.departure>d).distinct().count()
        revenue=db.query(func.coalesce(func.sum(Payment.amount),0)).join(Reservation).filter(Payment.status=="paid",Reservation.status!="cancelled",func.date(Payment.paid_at)==d).scalar() or 0
        rows.append({"date":d.isoformat(),"occupied":occupied,"revenue":float(revenue)})
    return rows
@app.get("/api/analytics/correlation",tags=["Tahlil"])
def correlation(db:Session=Depends(get_db),_:User=Depends(require_roles("administrator","manager"))):
    rows=db.query(Reservation,Room,RoomType).join(Room,Reservation.room_id==Room.id).join(RoomType,Room.room_type_id==RoomType.id).filter(Reservation.status!="cancelled").all()
    values=[[((r.departure-r.arrival).days),t.price_per_night,((r.departure-r.arrival).days)*t.price_per_night] for r,room,t in rows]
    if len(values)<2:return {"count":len(values),"matrix":[],"labels":["Tunlar","Narx","Bron summasi"]}
    import numpy as np
    return {"count":len(values),"labels":["Tunlar","Narx","Bron summasi"],"matrix":np.corrcoef(np.array(values).T).round(3).tolist()}
@app.get("/api/analytics/model-metrics",tags=["ML"])
def model_metrics(threshold:float=Query(.5,ge=.05,le=.95),_:User=Depends(require_roles("administrator","manager"))):
    _,reg,_,_,_=ml.models();return {"regression":reg,"classification":ml.classification_metrics(threshold),"threshold":threshold,"data_note":"Sintetik o‘quv ma’lumotlari; haqiqiy mehmonxona tarixi bilan qayta o‘qitish talab etiladi."}
@app.post("/api/analytics/predict/revenue",tags=["ML"])
def revenue_prediction(data:dict,_:User=Depends(require_roles("administrator","manager","receptionist"))):
    price=float(data.get("price_per_night",0));nights=int(data.get("nights",1));lead=int(data.get("lead_days",0));weekend=bool(data.get("weekend",False))
    if price<=0 or not 1<=nights<=60 or not 0<=lead<=365:raise HTTPException(400,"Kiritilgan qiymatlar diapazondan tashqarida")
    return ml.predict_revenue(price,nights,lead,weekend)
@app.post("/api/analytics/predict/cancellation",tags=["ML"])
def cancel_prediction(data:dict,_:User=Depends(require_roles("administrator","manager","receptionist"))):
    price=float(data.get("price_per_night",0));nights=int(data.get("nights",1));lead=int(data.get("lead_days",0));weekend=bool(data.get("weekend",False));threshold=float(data.get("threshold",.5))
    if price<=0 or not 1<=nights<=60 or not 0<=lead<=365 or not .05<=threshold<=.95:raise HTTPException(400,"Kiritilgan qiymatlar diapazondan tashqarida")
    return ml.predict_cancel(price,nights,lead,weekend,threshold)

app.mount("/", StaticFiles(directory="app/static",html=True), name="static")
