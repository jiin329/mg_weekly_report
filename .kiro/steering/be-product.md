---
title: Product
inclusion: manual
---

# 주간보고 채팅 데스크톱 앱 — Product

## 프로젝트 목적

카카오톡 데스크톱 클라이언트와 같은 단일 독립 실행형 데스크톱 애플리케이션을 구축한다. 사용자는 채팅 형태로 자유롭게 업무 내용을 입력하고, LLM이 이를 분석하여 구조화된 주간보고서를 자동 생성한다. 내부적으로 React + TypeScript(Frontend)와 Python + FastAPI(Backend)를 pywebview로 통합하여, 브라우저 없이 하나의 네이티브 데스크톱 창으로 제공한다.

## 제품 방향

- Phase 1 (현재): 개발자 PC에서 로컬 실행. 문서화된 명령으로 앱을 구동하면 데스크톱 창이 열림
- Phase 2 (추후): 단일 Windows Installer(PyInstaller + Inno Setup)로 패키징. 개발 도구 없이 설치·실행

## 핵심 기능 (Phase 1)

- 인증 없이 앱 실행 즉시 채팅방 사용 가능
- 자유 형식 텍스트로 무제한 메시지 입력 (카카오톡 스타일 UI)
- '주간보고 생성' 버튼 클릭 시 LLM이 전체 채팅 내용 분석 → 구조화된 주간보고서 생성
- 보고서 생성 시 해당 채팅방 Closed 전환 + 신규 Active 채팅방 자동 생성
- Closed 채팅방은 읽기 전용으로 보고서와 메시지 열람 가능
- 채팅방 목록 탐색 (Active/Closed 시각적 구분)
- 보고서 클립보드 복사

## 보고서 출력 구조 (Weekly_Report)

- 작성일 (writtenDate)
- 금주 업무 실적 (achievements)
- 차주 업무 계획 (nextWeekPlan)
- 이슈 및 건의사항 (issues)

## 사용자

- 주간보고를 작성해야 하는 팀원 (13명)
- 보고를 받는 관리자/리더

## 비즈니스 규칙

- 인증/로그인 없음 — 앱 실행 즉시 사용
- Active 채팅방은 시스템 전체에서 최대 1개만 존재
- 메시지가 없는 방에서는 보고서 생성 불가
- 보고서 생성 성공 시 원자적으로: (1) 보고서 저장, (2) 방 Closed 전환, (3) 신규 Active 방 생성
- Closed 방에서는 메시지 입력과 보고서 생성 모두 불가
- 공백 전용 메시지는 전송 거부 (FE 선제 차단 + BE 방어)
- 데이터는 로컬 영속 저장소에 보관 (앱 재시작 간 유지)

## 데스크톱 앱 구조

- 데스크톱 셸: pywebview (Python 네이티브 webview)
- Frontend: React + TypeScript (빌드된 정적 자산을 webview에 로드)
- Backend: Python + FastAPI (로컬 백그라운드 스레드, 127.0.0.1:{PORT})
- 외부 통신: LLM API 호출에만 한정
- FE↔BE 통신: 루프백 HTTP (127.0.0.1)

## REST API 엔드포인트

| 메서드 & 경로 | 설명 |
|----------------|------|
| `POST /rooms` | 새 Chat_Room 생성 |
| `GET /rooms` | 채팅방 목록 조회 |
| `GET /rooms/{roomId}/messages` | 방 내 메시지 조회 (시간순) |
| `POST /rooms/{roomId}/messages` | 메시지 전송 |
| `POST /rooms/{roomId}/report` | 주간보고 생성 요청 |

## 환경 변수

- `LLM_API_KEY`: LLM API 인증 키 (필수, 누락 시 시작 차단)
- `LLM_ENDPOINT`: LLM API 엔드포인트 URL (필수, 누락 시 시작 차단)
- `BACKEND_PORT`: 로컬 서버 포트 (기본값 제공)

## 오류 코드 카탈로그

| code | HTTP | 상황 |
|------|------|------|
| `ROOM_NOT_FOUND` | 404 | 존재하지 않는 room id |
| `ROOM_CLOSED` | 409 | Closed 방에 메시지/보고서 요청 |
| `EMPTY_MESSAGE` | 400 | 공백 전용 메시지 전송 |
| `NO_MESSAGES` | 400 | 메시지 없는 방의 보고서 생성 |
| `LLM_UNAVAILABLE` | 502 | LLM API 미도달/오류 |
| `LLM_TIMEOUT` | 504 | LLM 응답 시간 초과 |
| `CONFIG_MISSING` | 500 | 필수 LLM 설정 누락 (실행 중) |
| `INTERNAL_ERROR` | 500 | 그 외 내부 오류 |

## 협업 규칙

### Git 브랜치 전략

- `main` — 기본 브랜치, 모든 feature 브랜치의 base
- `feature/{FE|BE|LLM|SHARED|INTEGRATION}-{이름}` — 기능 개발 (main에서 분기)
- `fix/{FE|BE|...}-{이름}` — 버그 수정 (main에서 분기)
- `hotfix/{설명}` — 긴급 수정

### 커밋 메시지 (Conventional Commits)

```
<type>(<scope>): <subject>

예시:
feat(room): 채팅방 생성 API 추가
feat(report): 주간보고 생성 흐름 구현
fix(message): 공백 메시지 방어 로직 수정
feat(shell): pywebview 데스크톱 셸 통합
docs(readme): 로컬 실행 가이드 업데이트
test(report): 보고서 라이프사이클 속성 테스트 추가
```

허용 type: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

### PR 규칙

- PR 제목은 커밋 메시지 포맷과 동일
- 본문: 변경 사항 요약, 관련 요구사항 번호, 테스트 방법
- 최소 1명 이상 리뷰 승인 후 머지
- squash merge 기본 사용

### 코드 리뷰 체크리스트

- [ ] 비즈니스 요구사항을 정확히 구현했는가
- [ ] 네이밍 컨벤션을 따르는가
- [ ] 에러 핸들링이 적절한가 (구조화 오류 형식 준수)
- [ ] 불필요한 코드/주석이 없는가
- [ ] 테스트가 포함되어 있는가
- [ ] API 응답 포맷이 통일되어 있는가
- [ ] 데이터 모델 불변식을 위반하지 않는가
