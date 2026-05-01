# PDF Listener — FastAPI Backend

Backend for the [PDF Listener Flutter app](https://github.com/PratyushNayak99/pdflistener).  
Converts uploaded PDF/DOCX documents into audio (MP3) and serves them to the mobile client.

---

## Project Structure

```
pdflistener-backend/
├── app/
│   ├── main.py                      # FastAPI app + lifespan
│   ├── core/
│   │   ├── config.py                # Settings (pydantic-settings + .env)
│   │   ├── database.py              # SQLAlchemy engine + get_db dependency
│   │   └── security.py             # JWT + password hashing + get_current_user
│   ├── models/
│   │   ├── user.py                  # User ORM model
│   │   ├── file_item.py             # FileItem ORM model  ← mirrors Dart FileItem
│   │   └── notification_item.py    # NotificationItem ORM model ← mirrors Dart model
│   ├── schemas/
│   │   ├── user.py                  # Pydantic request/response schemas
│   │   ├── file_item.py
│   │   └── notification_item.py
│   ├── services/
│   │   ├── conversion.py           # PDF/DOCX → text → MP3 pipeline
│   │   └── notifications.py        # Helpers to create conversion notifications
│   └── api/v1/endpoints/
│       ├── auth.py                  # POST /register, POST /login
│       ├── users.py                 # GET/PATCH /users/me
│       ├── files.py                 # Upload, list, get, stream, delete
│       └── notifications.py        # List, mark read
├── uploads/                         # Uploaded source documents (auto-created)
├── audio_output/                    # Generated MP3 files (auto-created)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

```bash
# 1. Clone and enter the project
cd pdflistener-backend

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — at minimum change SECRET_KEY

# 5. Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The database (SQLite) and all tables are created automatically on first startup.  
Interactive docs: **http://localhost:8000/docs**

---

## API Reference

### Auth
| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/auth/register` | Create account |
| `POST` | `/api/v1/auth/login` | Get JWT token |

All other endpoints require: `Authorization: Bearer <token>`

### Users (Settings screen)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/users/me` | Get profile |
| `PATCH`| `/api/v1/users/me` | Update name, dark_mode, notifications_enabled |

### Files (Upload + Library + Player screen)
| Method | Path | Description |
|--------|------|-------------|
| `POST`   | `/api/v1/files/upload` | Upload document → starts background conversion |
| `GET`    | `/api/v1/files/` | List all files (Library screen) |
| `GET`    | `/api/v1/files/{id}` | Get single file — poll for processing status |
| `GET`    | `/api/v1/files/{id}/audio` | Stream MP3 (used by just_audio in Player screen) |
| `DELETE` | `/api/v1/files/{id}` | Delete file (swipe-to-delete in Library screen) |

#### Processing Status Flow
```
PENDING → PROCESSING → COMPLETED
                     ↘ FAILED
```
The Flutter Processing screen should poll `GET /files/{id}` every 1–2 seconds until
`status == "completed"` or `status == "failed"`.

### Notifications (Notifications screen)
| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/api/v1/notifications/` | List all + unread_count |
| `POST` | `/api/v1/notifications/mark-all-read` | Mark all read (Mark All Read button) |
| `PATCH`| `/api/v1/notifications/{id}/read` | Mark one read |

---

## Flutter Integration Guide

### 1. Register + Login
```dart
// Register
final res = await http.post(Uri.parse('$baseUrl/api/v1/auth/register'),
  body: jsonEncode({'name': name, 'email': email, 'password': password}),
  headers: {'Content-Type': 'application/json'},
);

// Login → store access_token
final res = await http.post(Uri.parse('$baseUrl/api/v1/auth/login'),
  body: jsonEncode({'email': email, 'password': password}),
  headers: {'Content-Type': 'application/json'},
);
final token = jsonDecode(res.body)['access_token'];
```

### 2. Upload + Poll
```dart
// Upload (multipart form)
final req = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/v1/files/upload'));
req.headers['Authorization'] = 'Bearer $token';
req.files.add(await http.MultipartFile.fromPath('file', filePath));
final res = await req.send();
final fileItem = jsonDecode(await res.stream.bytesToString());

// Poll until status == 'completed'
while (true) {
  await Future.delayed(Duration(seconds: 2));
  final poll = await http.get(
    Uri.parse('$baseUrl/api/v1/files/${fileItem['id']}'),
    headers: {'Authorization': 'Bearer $token'},
  );
  final data = jsonDecode(poll.body);
  if (data['status'] == 'completed') break;
  if (data['status'] == 'failed') throw Exception('Conversion failed');
}
```

### 3. Play Audio (just_audio)
```dart
final audioUrl = '$baseUrl/api/v1/files/${fileItem['id']}/audio';
await _audioPlayer.setUrl(audioUrl, headers: {'Authorization': 'Bearer $token'});
_audioPlayer.play();
```

---

## TTS Engines

| Engine | Quality | Cost | Setup |
|--------|---------|------|-------|
| **gTTS** (default) | Good | Free | Needs internet; set `TTS_ENGINE=gtts` |
| **OpenAI TTS** | Excellent | ~$0.015/1K chars | Set `TTS_ENGINE=openai` and `OPENAI_API_KEY=...` |

---

## Production Notes

- **Database**: Switch to PostgreSQL by updating `DATABASE_URL` in `.env`
- **File storage**: Move to S3/GCS and return presigned URLs instead of local `FileResponse`
- **Background jobs**: Replace `BackgroundTasks` with Celery + Redis for reliability
- **Secret key**: Use a cryptographically random 64-char string
- **HTTPS**: Put behind nginx or use a cloud load balancer with TLS
