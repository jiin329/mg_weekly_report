# weekly-report-chat

카카오톡 데스크톱 클라이언트 스타일의 단일 독립 실행형 데스크톱 애플리케이션(Desktop_App).
사용자는 로그인 없이 채팅으로 업무 내용을 남기고 '주간보고 생성' 버튼을 누르면 LLM이
구조화된 주간보고서를 생성한다. 브라우저 탭이 아닌 자체 네이티브 창(Application_Window)으로 제공된다.

내부 구성:

- **Frontend** — React + TypeScript (Vite). pywebview 창 안에 렌더링.
- **Backend** — Python + FastAPI. `127.0.0.1`의 로컬 루프백 REST 서버.
- **Desktop shell** — `app.py` (pywebview). FastAPI를 백그라운드로 기동하고 창을 연다.

> 이 저장소는 현재 **파운데이션 스켈레톤(task 1.1)** 단계다. 채팅방/메시지/보고서 등
> 비즈니스 로직은 이후 `[FE]`/`[BE]`/`[LLM]`/`[INTEGRATION]` 트랙에서 구현된다.

## 프로젝트 구조

```
.
├─ app.py              # 데스크톱 셸 진입점 (pywebview) — 부트스트랩 스켈레톤
├─ .env.example        # 환경 변수 예시 (LLM_API_KEY, LLM_ENDPOINT, BACKEND_PORT)
├─ frontend/           # React + TypeScript (Vite + Vitest)
└─ backend/            # Python + FastAPI (pytest + Hypothesis)
```

## 사전 준비 — 환경 변수 설정 (Requirement 10.5)

시작 전에 `.env.example`를 복사하여 `.env`를 만들고 값을 채운다.

```
copy .env.example .env      # Windows
# 또는
cp .env.example .env        # macOS/Linux
```

| 변수 | 필수 | 설명 |
|------|------|------|
| `LLM_API_KEY` | 예 | 외부 LLM 서비스 API 키. 비어 있으면 백엔드 기동 중단 |
| `LLM_ENDPOINT` | 예 | 외부 LLM 서비스 엔드포인트 URL. 비어 있으면 백엔드 기동 중단 |
| `BACKEND_PORT` | 아니오 | 백엔드 로컬 루프백 포트. 기본값 `8756` |

## Phase 1 — 로컬 실행 명령 (Requirement 10.4)

### Backend

```
cd backend
py -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell/CMD)
pip install -e ".[dev]"          # 또는: pip install -r requirements-dev.txt
pytest                           # 백엔드 테스트
# 개발용 서버 단독 실행(선택):
uvicorn app.main:app --host 127.0.0.1 --port 8756
```

### Frontend

```
cd frontend
npm install
npm run build       # 타입체크 + 프로덕션 빌드
npm test            # Vitest
npm run dev         # 개발 서버(선택, 브라우저 미리보기용)
```

### Desktop_App (데스크톱 창)

```
# 프로젝트 루트에서 (frontend 빌드 및 backend 의존성 설치 후)
python app.py
```

> `python app.py`의 전체 통합(FastAPI 백그라운드 기동 + pywebview 창)은 통합 단계
> (task 8.3)에서 구현된다. 현재는 부트스트랩 흐름을 문서화한 스켈레톤이다.

## 테스트 도구

- **Frontend**: Vitest (+ @testing-library/react, fast-check) — `npm test`
- **Backend**: pytest (+ Hypothesis) — `pytest`
