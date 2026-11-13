# Mehmonxona boshqaruvi MVP

FastAPI + PostgreSQL asosidagi sodda, to‘liq qatlamli o‘quv loyihasi. Bitta Docker buyrug‘i UI, REST API, PostgreSQL, demo ma’lumotlar va migratsiyani ishga tushiradi.

## Ishga tushirish

Talablar: Docker va Docker Compose.

```bash
cp .env.example .env
# .env ichidagi SECRET_KEY va ADMIN_PASSWORD ni almashtiring
docker compose up --build
```

Brauzerda `http://localhost:8000` ni oching. OpenAPI hujjati `http://localhost:8000/docs`, health tekshiruvi `/api/health` manzilida.

### Linux’da Docker’siz ishga tushirish

Python 3.10+ va `python3-venv` kerak. Loyihaning papkasida terminal ochib:

```bash
./run-local.sh
```

Skript virtual muhit yaratadi, kutubxonalarni o‘rnatadi, lokal SQLite bazasini tayyorlaydi va serverni boshlaydi. Birinchi ishga tushishda internet kerak bo‘ladi. Server terminal oynasi ochiq turguncha ishlaydi; to‘xtatish uchun `Ctrl+C` bosing.

Demo hisoblar (ilk ko‘rish uchun):

| Rol | Login | Parol |
|---|---|---|
| Administrator | `admin` | `.env` dagi `ADMIN_PASSWORD` (standart: `Admin123!`) |
| Menejer | `manager` | `.env` dagi `DEMO_PASSWORD` (standart: `Demo123!`) |
| Qabulxona xodimi | `reception` | `.env` dagi `DEMO_PASSWORD` |
| Mehmon demo hisobi | `guest` | `.env` dagi `DEMO_PASSWORD` |

Demo parollarni haqiqiy muhitda ishlatmang. Birinchi ishga tushgach administrator hisobidan boshqa xodimlar uchun alohida hisob yarating. Yangi `guest` roli yaratilganda mehmon profili user IDsi bilan avtomatik bog‘lanadi; mehmon faqat o‘z bronlarini ko‘radi.

## Mavjud qismlar

- **Client:** FastAPI StaticFiles orqali beriladigan moslashuvchan Uzbek tilidagi dashboard; overview, bronlar, xonalar, mehmonlar, fayllar, tahlil/ML va administrator foydalanuvchilari sahifalari.
- **REST API:** `/api` prefiksi, JWT bearer kirishi, rolga asoslangan ruxsatlar, validatsiya, xato javoblari, log yozuvi va Swagger UI.
- **PostgreSQL:** users, guests, room_types, rooms, reservations, payments, services, reservation_services, uploaded_files jadvallari. Alembic `0001_initial` migratsiyasi ishga tushishda bajariladi.
- **CRUD va qoidalar:** xona, xona turi, mehmon, bron yaratish/o‘qish/holatini yangilash/o‘chirish; band sanalarga ikkinchi bron qo‘yishni rad etadi; to‘lov qo‘shish; rolli foydalanuvchi yaratish.
- **Fayl saqlash:** CSV, Excel, PDF, JPEG, PNG, WebP yuklash (12 MB gacha), metadata va autentifikatsiyalangan yuklab olish. Lokal Docker Compose named volume ishlatadi.
- **Tahlil:** bandlik, daromad, toifa kesimi, kunlik vaqt qatori, bron muddati va narx korrelyatsiyasi.
- **ML:** scikit-learn regression (daromad) va classification (bron bekor qilinishi), train/test split va MAE/RMSE/R²; confusion matrix, accuracy/precision/recall/F1 va o‘zgaradigan threshold. Bashorat endpointlari va UI mavjud. Namuna dataset sintetik, demo uchun.
- **Ishlab chiqarish tayyorgarligi:** Dockerfile, Compose, migration, pytest unit/integration testlari, GitHub Actions CI, Cloud Run/Cloud SQL/GCS deploy skripti, environment konfiguratsiyasi.

## Asosiy API

| Amal | Endpoint | Ruxsat |
|---|---|---|
| Kirish / profil | `POST /api/auth/login`, `GET /api/auth/me` | Ochiq / kirgan foydalanuvchi |
| Xonalar | `GET/POST /api/rooms`, `PATCH /api/rooms/{id}` | Kirgan / admin yoki menejer |
| Mehmonlar | `GET/POST /api/guests` | Kirgan / xodim |
| Bronlar | `GET/POST /api/reservations`, `PATCH /api/reservations/{id}/status`, `DELETE /api/reservations/{id}` | Kirgan / tegishli xodim |
| To‘lovlar | `POST /api/reservations/{id}/payments` | Xodim |
| Fayllar | `GET/POST /api/files`, `GET /api/files/{id}` | Kirgan / xodim |
| Tahlil | `GET /api/analytics/summary`, `/series`, `/correlation` | Xodim/menejer |
| ML | `GET /api/analytics/model-metrics`, `POST /api/analytics/predict/*` | Menejer / xodim |

## Testlar

Loyihada model va API integration testlari `tests/` ichida. Testlar local SQLite test DB bilan ajratilgan; CI PostgreSQL migratsiyani ham tekshiradi.

```bash
pip install -r requirements.txt
DATABASE_URL=sqlite:///./hotel_test.db SECRET_KEY=test-secret pytest -q
```

## Google Cloud Run

1. Artifact Registry repository, Cloud SQL PostgreSQL instance, DB va Cloud Storage bucket yarating.
2. Cloud Run service account-ga Cloud SQL Client, Secret Manager Secret Accessor va bucket uchun Storage Object User rollarini bering. Secret Manager’da `DATABASE_URL`, `SECRET_KEY`, `ADMIN_PASSWORD`, `DEMO_PASSWORD` sirlarini yarating.
3. Secret Manager ichida `DATABASE_URL` qiymatini `postgresql+psycopg2://USER:PASSWORD@/DB?host=/cloudsql/PROJECT:REGION:INSTANCE` ko‘rinishida va JWT kalitini saqlang.
4. `PROJECT_ID`, `REGION`, `INSTANCE_CONNECTION_NAME`, `DATABASE_SECRET`, `JWT_SECRET`, `ADMIN_SECRET`, `DEMO_SECRET`, `GCS_BUCKET` environmentlarini belgilang va `./deploy-cloud-run.sh` ishga tushiring.

Deploy skripti image build qilib Cloud Run’ga yuboradi. Fayllar GCS bucketga yoziladi. DB migratsiya va seed app startida bajariladi; production’da seed administrator parolini Secret Manager/environment orqali albatta o‘rnating.
