---
title: Structure
inclusion: manual
---

# 주간보고 채팅 데스크톱 앱 — Backend 구조 및 코딩 컨벤션

## 언어 및 프레임워크

- Python 3.11+
- FastAPI (REST API)
- pywebview (데스크톱 셸)
- Pydantic (데이터 모델/스키마)
- pydantic-settings (환경 변수 로딩)

## 디렉토리 구조

```
backend/
├── modules/
│   ├── room/
│   │   ├── router.py        # /rooms 엔드포인트
│   │   ├── service.py       # RoomService (라이프사이클 관리)
│   │   ├── repository.py    # 방 영속 저장소 접근
│   │   └── schemas.py       # ChatRoom Pydantic 모델
│   ├── message/
│   │   ├── router.py        # /rooms/{roomId}/messages 엔드포인트
│   │   ├── service.py       # MessageService (저장/조회/방어)
│   │   ├── repository.py    # 메시지 영속 저장소 접근
│   │   └── schemas.py       # Message Pydantic 모델
│   ├── report/
│   │   ├── router.py        # /rooms/{roomId}/report 엔드포인트
│   │   ├── service.py       # ReportService (프롬프트 구성/LLM 호출/파싱)
│   │   └── schemas.py       # WeeklyReport Pydantic 모델
│   └── llm/
│       ├── client.py         # LLMClient (API 연동)
│       ├── prompt.py         # 프롬프트 구성 로직
│       └── parser.py         # LLM 응답 → WeeklyReport 파싱
├── common/
│   ├── exceptions.py         # 커스텀 Exception + 오류 코드 카탈로그
│   ├── error_handlers.py     # 글로벌 예외 핸들러
│   └── dependencies.py       # FastAPI 의존성
├── config/
│   └── settings.py           # AppConfig (env 로딩/검증/영속)
├── store/                    # 로컬 영속 저장소 (SQLite 또는 파일 기반)
├── main.py                   # FastAPI 앱 엔트리포인트
├── app.py                    # 데스크톱 셸 진입점 (pywebview + FastAPI 스레드)
└── tests/
    ├── unit/
    └── integration/
frontend/                     # React + TypeScript (별도 빌드)
```

## 데이터 모델 (Pydantic)

### ChatRoom

```python
class ChatRoom(BaseModel):
    id: str                          # UUID
    status: Literal["active", "closed"]
    created_at: datetime
    closed_at: datetime | None = None
    report: WeeklyReport | None = None
```

불변식:
- `status == "closed"` → `report is not None` and `closed_at is not None`
- `status == "active"` → `report is None` and `closed_at is None`
- 전체 시스템에서 `active` 방은 최대 1개

### Message

```python
class Message(BaseModel):
    id: str                          # UUID
    room_id: str
    sender: Literal["user", "system"]
    content: str                     # user 메시지는 strip() 후 비어있지 않음
    created_at: datetime
```

### WeeklyReport

```python
class WeeklyReport(BaseModel):
    written_date: str                # 작성일
    achievements: str                # 금주 업무 실적
    next_week_plan: str              # 차주 업무 계획
    issues: str                      # 이슈 및 건의사항
```

### ErrorResponse

```python
class ErrorDetail(BaseModel):
    code: str                        # e.g. "ROOM_NOT_FOUND"
    message: str                     # 사람이 읽을 수 있는 설명
    details: Any | None = None
```

## 네이밍 규칙

- 파일명/모듈명: snake_case (`room_service.py`)
- 클래스: PascalCase (`RoomService`)
- 함수/변수: snake_case (`get_room_by_id`)
- 상수: UPPER_SNAKE_CASE (`MAX_LLM_TIMEOUT`)
- Pydantic 스키마: PascalCase (`CreateMessageRequest`, `ReportGenerationResponse`)
- API 경로: 복수형 명사, 버저닝 없음 (`/rooms`, `/rooms/{roomId}/messages`)

## 코드 스타일

- 함수는 단일 책임 원칙을 따른다
- 하나의 함수는 30줄 이내 권장
- 매직 넘버 사용 금지 — 상수로 추출
- 주석은 "왜(why)"를 설명할 때만 사용
- early return 패턴 적극 활용
- Type hint 필수 (함수 인자, 반환값 모두)
- docstring: 공개 함수/클래스에 Google style docstring 작성

## 에러 처리

- 비즈니스 예외는 `common/exceptions.py`에 커스텀 Exception으로 관리
- 글로벌 예외 핸들러에서 일괄 처리
- 모든 오류 응답은 구조화 형식 준수:
  ```json
  { "error": { "code": "ROOM_NOT_FOUND", "message": "요청한 채팅방을 찾을 수 없습니다.", "details": null } }
  ```
- HTTP 상태 코드 매핑: 400(클라이언트), 404(미발견), 409(충돌), 502(LLM 미도달), 504(LLM 타임아웃), 500(내부)
- LLM 실패 시 방은 Active 상태를 유지한다 (부분 상태 전이 없음)

## API 설계 규칙

- RESTful 원칙 준수
- 기본 경로: `http://127.0.0.1:{BACKEND_PORT}`
- 엔드포인트 5종만 존재 (오버엔지니어링 금지)
- `POST /rooms/{roomId}/report` 성공 시 원자적으로: 보고서 생성 → 방 Closed → 신규 Active 방 생성
- Closed 방에 대한 메시지/보고서 요청은 409로 거부
- 유효하지 않은 roomId는 404로 거부

## 데스크톱 셸 (app.py)

- Python 진입점에서 부트스트랩 수행:
  1. 환경 변수 검증 (누락 시 시작 차단, 변수명 명시)
  2. FastAPI 서버를 백그라운드 스레드로 기동
  3. 포트 바인딩 확인 (충돌 시 시작 차단, 포트 번호 명시)
  4. pywebview 창 생성 → 빌드된 React 정적 자산 로드
- 시작 실패 시 셸 수준 오류 창 표시

## 저장소 (Repository)

- 로컬 영속 저장소 사용 (인메모리 부적합 — 재시작 간 데이터 유지 필요)
- Phase 2 설정 영속성 지원 (LLM 설정값 재시작 간 보존)
- 단순한 구현 우선: SQLite 또는 JSON 파일 기반

## 테스트 기준

- 서비스 레이어: 단위 테스트 필수
- 라우터 레이어: 통합 테스트 권장
- 속성 기반 테스트: Python Hypothesis (최소 100회 반복)
- 테스트 파일 위치: `backend/tests/unit/`, `backend/tests/integration/`
- 테스트 파일명: `test_{모듈명}.py`
- LLM 의존성: stub/mock 클라이언트로 격리
- 커버리지 목표: 핵심 비즈니스 로직 80% 이상

## 환경 변수 관리

- `.env` 파일은 절대 커밋하지 않음 (`.gitignore`에 포함)
- `.env.example`에 필수 변수 목록 명시: `LLM_API_KEY`, `LLM_ENDPOINT`, `BACKEND_PORT`
- `config/settings.py`에서 pydantic-settings로 타입 안전하게 로딩
- 필수 변수 누락 시 시작 단계에서 차단하고 누락 변수명을 명시

## 오버스펙 방지 원칙

- 요청된 기능만 구현한다 (YAGNI)
- 추상화는 반복이 3회 이상 발생한 이후에 도입한다
- 디자인 패턴은 실제 문제를 해결할 때만 적용한다
- 불필요한 제네릭/인터페이스/팩토리를 만들지 않는다
- 한 PR에서 요구사항 외 리팩토링을 섞지 않는다
- 라이브러리/패키지 도입은 직접 구현 대비 명확한 이점이 있을 때만
- MVP 우선: 동작하는 최소 구현 → 피드백 → 점진적 개선

## 의존성 관리

- `pyproject.toml` 또는 `requirements.txt`로 관리
- 패키지 버전은 정확히 고정 (pinning)
- 핵심 의존성: fastapi, uvicorn, pywebview, pydantic, pydantic-settings, hypothesis(테스트)
- 새 패키지 추가 시 PR에 사유 명시
