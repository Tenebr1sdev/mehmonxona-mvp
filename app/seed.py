from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, Guest, RoomType, Room, Reservation, Payment, Service
from app.security import hash_password
import os

def seed(db: Session):
    if not db.query(User).filter_by(username=os.getenv("ADMIN_USERNAME","admin")).first():
        admin=User(username=os.getenv("ADMIN_USERNAME","admin"),full_name="Hotel Administrator",role="administrator",password_hash=hash_password(os.getenv("ADMIN_PASSWORD","Admin123!")))
        db.add(admin)
        for username,name,role in [("manager","Hotel Manager","manager"),("reception","Receptionist","receptionist"),("guest","Demo Guest","guest")]:
            if not db.query(User).filter_by(username=username).first():db.add(User(username=username,full_name=name,role=role,password_hash=hash_password(os.getenv("DEMO_PASSWORD","Demo123!"))))
        db.flush()
    if db.query(RoomType).count()==0:
        types=[RoomType(name="Standart",capacity=2,price_per_night=420000),RoomType(name="Komfort",capacity=3,price_per_night=620000),RoomType(name="Lyuks",capacity=4,price_per_night=950000)]
        db.add_all(types);db.flush()
        for prefix,typ,count in [("1",types[0],4),("2",types[1],4),("3",types[2],4)]:
            for n in range(1,count+1):db.add(Room(number=f"{prefix}0{n}",room_type_id=typ.id,state="maintenance" if prefix=="2" and n==4 else "active"))
        db.add_all([Service(name="Nonushta",price=85000),Service(name="Aeroport transferi",price=180000),Service(name="Kir yuvish",price=50000)])
        db.flush()
    demo_user=db.query(User).filter_by(username="guest").first()
    demo_guest=db.query(Guest).filter_by(user_id=demo_user.id).first() if demo_user else None
    if not demo_guest:
        demo_guest=Guest(full_name="Demo Guest",phone="+998 90 000 00 00",email="guest@example.com",user_id=demo_user.id if demo_user else None)
        db.add(demo_guest);db.flush()
    if db.query(Reservation).count()==0:
        today=date.today();samples=[("Aziza Rahimova","+998 90 245 16 30","301",-1,2,"staying","paid"),("Jasur Tursunov","+998 93 411 08 72","102",0,2,"confirmed","paid"),("Madina Ismoilova","+998 97 552 40 11","202",1,4,"confirmed","partial"),("Bekzod Aliyev","+998 90 718 33 04","101",-4,-2,"done","paid"),("Malika Qodirova","+998 99 103 75 62","302",3,5,"confirmed","unpaid"),("Sardor Ergashev","+998 95 204 18 76","103",0,1,"cancelled","unpaid")]
        for name,phone,number,start,end,status,pay in samples:
            guest=Guest(full_name=name,phone=phone);db.add(guest);db.flush();room=db.query(Room).filter_by(number=number).one();arr=today+timedelta(days=start);dep=today+timedelta(days=end)
            res=Reservation(code=f"H{guest.id:05d}",guest_id=guest.id,room_id=room.id,arrival=arr,departure=dep,status=status);db.add(res);db.flush()
            amount=(dep-arr).days*room.room_type.price_per_night
            if pay=="paid":db.add(Payment(reservation_id=res.id,amount=amount,status="paid"))
            elif pay=="partial":db.add(Payment(reservation_id=res.id,amount=amount/2,status="paid"))
    db.commit()

if __name__=="__main__":
    db=SessionLocal()
    try:seed(db)
    finally:db.close()
