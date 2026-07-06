# Implementation Plan: weekly-report-chat

## Overview

본 구현 계획은 3명의 병렬 작업자(Frontend, Backend, LLM)가 상호 간섭을 최소화하며 동시에 작업할 수 있도록 구성되었다. 전체 흐름은 다음과 같다.

1. **[SHARED] 파운데이션 / 계약 단계** — 세 트랙이 공통으로 의존하는 계약(REST API 스펙, 공유 데이터 모델/타입, LLM 모듈 인터페이스 경계, 저장소 스켈레톤, 로컬 포트/설정)을 한 번에 확정한다. 이 단계가 끝나면 세 트랙은 계약의 mock/stub만 의존하며 서로 독립적으로 진행된다.
2. **3개 독립 트랙** — `[FE]` Frontend, `[BE]` Backend, `[LLM]` LLM 트랙이 파운데이션 이후 상호 의존 없이 병렬 진행된다. FE는 mock 백엔드, BE는 stub LLM 클라이언트를 사용해 각자 완결적으로 개발·테스트한다.
3. **[INTEGRATION] 통합 단계** — 실제 LLM을 BE에 연결하고, FE를 실제 BE에 연결하며, pywebview 데스크톱 셸 통합, E2E 보고서 흐름, Phase 2 패키징(PyInstaller + Inno Setup)을 수행한다.

**트랙 태그 규칙**: 각 작업에는 소유 트랙을 나타내는 접두 태그(`[SHARED]`, `[FE]`, `[BE]`, `[LLM]`, `[INTEGRATION]`)를 붙인다.

**의존성 원칙**: 파운데이션(작업 1) 완료 후 FE/BE/LLM 세 트랙은 서로 의존하지 않는다. 각 트랙은 확정된 계약의 mock/stub에만 의존하며, 실제 연결은 통합 단계에서만 발생한다.

---

## Tasks

- [x] 1. [SHARED] 파운데이션 / 계약 확정
  - [x] 1.1 [SHARED] 저장소·프로젝트 스켈레톤 및 로컬 설정 구성
    - `frontend/`(React + TypeScript), `backend/`(Python + FastAPI) 폴더 구조와 데스크톱 셸 진입점(`app.py` 등) 스켈레톤 생성
    - 로컬 루프백 포트(`BACKEND_PORT` 기본값 포함) 및 `.env.example`(LLM_API_KEY, LLM_ENDPOINT, BACKEND_PORT) 합의·명시
    - FE/BE 각각의 빌드·테스트 도구(예: Vite/Vitest, pytest/Hypothesis) 초기 설정
    - _Requirements: 8.1, 9.5, 10.4, 10.5_
    - _블로킹: 이후 모든 작업의 선행 조건_
  - [x] 1.2 [SHARED] 공유 데이터 모델/타입 정의
    - TypeScript 타입(`ChatRoom`, `Message`, `WeeklyReport`, `ErrorResponse`, `AppConfig`)을 `frontend/`에 정의
    - Python 대응 모델(Pydantic 스키마)을 `backend/`에 정의하고 두 정의가 동일 계약을 표현하도록 정합성 확보
    - 데이터 모델 불변식(방 status↔report/closedAt 관계, active 방 최대 1개, user 메시지 공백 불가) 주석 명시
    - _Requirements: 1.3, 3.4, 5.2_
    - _블로킹: 1.3, 1.5 및 FE/BE 트랙_
  - [x] 1.3 [SHARED] REST API 계약 확정
    - design.md의 엔드포인트 5종(`POST /rooms`, `GET /rooms`, `GET /rooms/{roomId}/messages`, `POST /rooms/{roomId}/messages`, `POST /rooms/{roomId}/report`)에 대한 요청/응답 형태를 계약 문서/타입으로 고정
    - 각 엔드포인트의 동작 규칙(Closed 방 메시지 거부, 메시지 없는 방 보고서 거부, 원자적 보고서 생성 흐름) 명시
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 3.1, 3.5, 4.2, 5.3, 6.1, 6.2, 6.3_
    - _블로킹: FE/BE 트랙_
  - [x] 1.4 [SHARED] 오류 코드 카탈로그 및 구조화 오류 형식 확정
    - `ErrorResponse` 구조(`error.code`, `error.message`, `error.details?`) 및 코드 카탈로그(`ROOM_NOT_FOUND`, `ROOM_CLOSED`, `EMPTY_MESSAGE`, `NO_MESSAGES`, `LLM_UNAVAILABLE`, `LLM_TIMEOUT`, `CONFIG_MISSING`, `INTERNAL_ERROR`)를 공유 상수로 정의
    - HTTP 상태 코드 매핑 명시
    - _Requirements: 8.7, 8.8_
    - _블로킹: BE/FE 트랙(오류 파싱)_
  - [x] 1.5 [SHARED] LLM 모듈 인터페이스 경계 및 stub/mock 계약 정의
    - LLM 모듈 인터페이스(입력: user 메시지 목록 + Report_Template, 출력: 파싱된 `WeeklyReport`) 시그니처 확정 (예: `LLMClient.generate(messages, template) -> WeeklyReport`)
    - BE와 LLM 트랙이 공유할 stub/mock 클라이언트(고정 응답 반환) 구현 — BE는 이 stub로 개발, LLM 트랙은 실제 구현을 이 인터페이스에 맞춰 개발
    - 타임아웃/오류(`LLM_UNAVAILABLE`, `LLM_TIMEOUT`) 계약 명시
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
    - _블로킹: BE(ReportService), LLM 트랙_

- [x] 2. [SHARED] 체크포인트 — 계약 정합성 확인
  - 모든 테스트가 통과하는지 확인하고, 계약(타입/엔드포인트/오류/LLM 인터페이스)이 세 트랙에서 동일하게 참조 가능한지 검토한다. 의문점이 있으면 사용자에게 확인한다.

- [ ] 3. [FE] Frontend 트랙 (mock 백엔드 대상 개발, BE 진행에 비의존)
  - [ ] 3.1 [FE] apiClient 및 mock 백엔드 하네스 구현
    - 확정된 REST 계약(1.3)에 대한 `apiClient` fetch 래퍼 구현, 구조화 오류 응답(1.4) 파싱
    - FE 단독 개발을 위한 mock 백엔드(고정/메모리 응답) 하네스 구성 — 실제 BE 없이 전체 UI 흐름 검증 가능
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_
    - _의존: 1.2, 1.3, 1.4 / BE·LLM 트랙에 비의존_
  - [ ] 3.2 [FE] AppShell 레이아웃 및 창 리사이즈 대응 구현
    - 사이드바 + 메인 채팅 영역 레이아웃, Application_Window 리사이즈 시 레이아웃 적응
    - _Requirements: 2.6, 7_
    - _의존: 3.1_
  - [ ] 3.3 [FE] RoomList 컴포넌트 구현
    - Active/Closed 채팅방 목록 표시 및 시각적 구분, 선택 시 방 전환, 기본으로 최신 Active 방 표시
    - 앱 로드 시 기존 Active 방과 그 이전 메시지를 표시(신규 첫 실행이 아닌 경우)
    - _Requirements: 1.4, 7.1, 7.2, 7.3, 7.4_
    - _의존: 3.1_
  - [ ] 3.4 [FE] MessageList 컴포넌트 및 자동 스크롤 구현
    - 메시지 스크롤 영역, 신규 메시지 추가 시 최신 메시지로 자동 스크롤
    - _Requirements: 2.5_
    - _의존: 3.1_
  - [ ] 3.5 [FE] MessageBubble 컴포넌트 구현
    - User 메시지(우측 정렬/구분 색상), 시스템 보고서 메시지(좌측 정렬/다른 색상), 각 메시지 타임스탬프 표시
    - _Requirements: 2.1, 2.2, 2.3_
    - _의존: 3.1_
  - [ ] 3.6 [FE] InputArea 컴포넌트 구현
    - Application_Window 하단의 텍스트 입력 필드 + 전송 버튼, Enter 전송, 빈/공백 메시지 전송 차단(오류 미표시), Closed 방에서 입력·전송 비활성화
    - _Requirements: 2.4, 3.1, 3.2, 3.3, 6.2, 6.6_
    - _의존: 3.1_
  - [ ] 3.7 [FE] GenerateButton 컴포넌트 구현
    - Active 방에서만 '주간보고 생성' 버튼 노출, 메시지 없으면 생성 차단 및 안내 표시, 클릭 시 보고서 생성 요청
    - _Requirements: 4.1, 4.2, 4.5_
    - _의존: 3.1_
  - [ ] 3.8 [FE] ReportCard 및 LoadingIndicator 구현
    - 생성된 Weekly_Report 4개 섹션 포맷 표시, 복사 버튼 및 복사 성공 알림, 생성 대기 중 로딩 인디케이터 표시
    - _Requirements: 4.4, 5.4, 5.5, 5.6_
    - _의존: 3.1_
  - [ ] 3.9 [FE] ConnectionErrorBanner 구현
    - Backend 연결 불가 시 Application_Window 내 오류 배너 표시
    - _Requirements: 10.9, 11.6_
    - _의존: 3.1_
  - [ ]* 3.10 [FE] MessageBubble 타임스탬프 렌더 속성 테스트
    - **Property 5: 렌더된 메시지는 항상 타임스탬프를 포함한다**
    - **Validates: Requirements 2.3**
    - fast-check + React Testing Library로 임의 유효 메시지에 대해 렌더 출력에 타임스탬프 포함 검증
    - _의존: 3.5_
  - [ ]* 3.11 [FE] UI 예시/스냅샷 단위 테스트
    - 메시지 버블 정렬·색상(2.1, 2.2), 입력 영역(2.4), 자동 스크롤(2.5), 방 목록/구분/선택/기본표시(7.1–7.4), Closed 방 입력 비활성(6.2), 신규 방 노출(6.4), 읽기 전용 조회(6.5), 로딩 표시(4.4), 보고서 카드·복사(5.4–5.6), 연결 오류 배너(10.9)
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 4.4, 5.4, 5.5, 5.6, 6.2, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 10.9_
    - _의존: 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

- [ ] 4. [BE] Backend 트랙 (stub LLM 클라이언트 대상 개발, FE·LLM 진행에 비의존)
  - [ ] 4.1 [BE] Config 로딩 및 환경 변수 검증 구현
    - `LLM_API_KEY`, `LLM_ENDPOINT`, `BACKEND_PORT` 로딩 및 검증, 누락 항목을 이름으로 식별하는 시작 오류, 실행 중 `CONFIG_MISSING` 처리
    - 설정값 영속 저장/재로딩(Phase 2 대비) 계층 구현
    - _Requirements: 9.5, 10.6, 11.8, 11.9_
    - _의존: 1.1, 1.2 / FE·LLM 트랙에 비의존_
  - [ ] 4.2 [BE] Repository(로컬 영속 저장소) 구현
    - 방/메시지/보고서 영속 저장·조회 계층, 재시작 간 데이터 유지 (인메모리 부적합)
    - _Requirements: 3.4, 8.4_
    - _의존: 1.2_
  - [ ] 4.3 [BE] Pydantic 데이터 모델 및 불변식 구현
    - `ChatRoom`, `Message`, `WeeklyReport`, `ErrorResponse` 모델과 불변식(status↔report/closedAt, user 메시지 공백 불가) 구현
    - _Requirements: 1.3, 3.3, 5.2_
    - _의존: 1.2_
  - [ ] 4.4 [BE] RoomService(라이프사이클) 구현
    - 방 생성/조회/목록, Active↔Closed 전이, 보고서 성공 시 원자적으로 Closed 전환 + 신규 Active 방 생성, active 방 최대 1개 불변식 유지
    - _Requirements: 1.3, 6.1, 6.3, 7.1, 8.2, 8.6_
    - _의존: 4.2, 4.3_
  - [ ] 4.5 [BE] MessageService 구현
    - 메시지 시간순 저장·조회, 공백 전용 메시지 방어, Closed 방 메시지 거부
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 6.6_
    - _의존: 4.2, 4.3_
  - [ ] 4.6 [BE] FastAPI 라우터·엔드포인트 및 구조화 오류 핸들링 구현
    - 계약(1.3)의 5개 엔드포인트 구현, 유효하지 않은 roomId 및 내부 오류를 오류 카탈로그(1.4)에 따라 구조화 응답으로 반환
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 6.6_
    - _의존: 4.4, 4.5_
  - [ ] 4.7 [BE] ReportService를 stub LLM 클라이언트로 연결
    - 방 메시지 취합 → LLM 인터페이스(1.5) 호출 → 응답을 `WeeklyReport`로 수용하는 보고서 생성 흐름 구현, 메시지 없는 방 차단(`NO_MESSAGES`), 실패 시 방 Active 유지(부분 전이 없음)
    - stub LLM 클라이언트(1.5)를 사용하여 실제 LLM 트랙에 비의존
    - _Requirements: 4.2, 4.3, 5.3, 5.7, 6.1, 9.4_
    - _의존: 4.4, 4.6, 1.5_
  - [ ]* 4.8 [BE] 방 생성 속성 테스트
    - **Property 1: 방 생성은 항상 유효한 Active 방을 반환한다**
    - **Validates: Requirements 1.3, 8.2**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.4, 4.6_
  - [ ]* 4.9 [BE] 메시지 저장 개수 속성 테스트
    - **Property 2: Active 방은 임의 개수의 메시지를 모두 저장한다**
    - **Validates: Requirements 3.2**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.5, 4.6_
  - [ ]* 4.10 [BE] 메시지 라운드트립 속성 테스트
    - **Property 3: 메시지 전송-조회 라운드트립**
    - **Validates: Requirements 3.1, 8.3, 8.4**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.5, 4.6_
  - [ ]* 4.11 [BE] 메시지 시간순 보존 속성 테스트
    - **Property 4: 메시지는 시간순으로 보존된다**
    - **Validates: Requirements 3.4**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.5, 4.6_
  - [ ]* 4.12 [BE] 공백 메시지 거부 속성 테스트
    - **Property 6: 공백 전용 메시지는 거부된다**
    - **Validates: Requirements 3.3**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.5, 4.6_
  - [ ]* 4.13 [BE] 보고서 생성 라이프사이클 속성 테스트
    - **Property 9: 보고서 생성 성공 시 라이프사이클 불변식이 유지된다**
    - **Validates: Requirements 6.1, 6.3, 8.5, 8.6**
    - Hypothesis, 최소 100회 반복, stub LLM 사용
    - _의존: 4.7_
  - [ ]* 4.14 [BE] Closed 방 거부 속성 테스트
    - **Property 10: Closed 방은 메시지 입력과 보고서 생성을 거부한다**
    - **Validates: Requirements 6.6**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.6, 4.7_
  - [ ]* 4.15 [BE] 구조화 오류 응답 속성 테스트
    - **Property 11: 오류 응답은 항상 구조화 형식이다**
    - **Validates: Requirements 8.7, 8.8**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.6_
  - [ ]* 4.16 [BE] 설정 누락 차단 속성 테스트
    - **Property 12: 필수 LLM 설정 누락 시 항상 차단하고 누락 항목을 식별한다**
    - **Validates: Requirements 10.6, 11.9**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.1_
  - [ ]* 4.17 [BE] 설정 영속성 속성 테스트
    - **Property 13: 설치 후 설정값은 재시작 간 영속된다**
    - **Validates: Requirements 11.8**
    - Hypothesis, 최소 100회 반복
    - _의존: 4.1_
  - [ ]* 4.18 [BE] Backend 예시/엣지 케이스 단위 테스트
    - 메시지 없는 방 보고서 차단(4.5/`NO_MESSAGES`), LLM 실패 오류 경로(5.7, 9.4), 포트 충돌(10.8), 유효하지 않은 roomId(8.7) 예시 테스트
    - _Requirements: 4.5, 5.7, 8.7, 9.4, 10.8_
    - _의존: 4.6, 4.7_

- [ ] 5. [BE][FE] 체크포인트 — 트랙별 단독 검증
  - FE(mock 백엔드) 및 BE(stub LLM) 각 트랙의 모든 테스트가 통과하는지 확인한다. 의문점이 있으면 사용자에게 확인한다.

- [ ] 6. [LLM] LLM 트랙 (합의된 인터페이스 뒤에서 독립 개발, FE·BE 진행에 비의존)
  - [ ] 6.1 [LLM] LLMClient 구현 (env 기반 API Key/Endpoint)
    - 환경 변수 기반 LLM API 연동 클라이언트, 인터페이스 경계(1.5) 준수
    - _Requirements: 9.1, 9.5_
    - _의존: 1.5, 4.1 계약(설정 형태만) / FE·BE 트랙 코드에 비의존_
  - [ ] 6.2 [LLM] 프롬프트 구성 로직 구현
    - user 메시지 목록 + Report_Template(작성일, 금주 업무 실적, 차주 업무 계획, 이슈 및 건의사항) 섹션 지시를 포함하는 구조화 프롬프트 생성
    - _Requirements: 4.3, 9.2_
    - _의존: 1.5_
  - [ ] 6.3 [LLM] 응답 파싱 로직 구현
    - LLM 응답을 `WeeklyReport`(네 섹션 모두 포함) 구조로 파싱
    - _Requirements: 5.1, 5.2, 9.3_
    - _의존: 1.5_
  - [ ] 6.4 [LLM] 타임아웃·오류 처리 구현
    - LLM 미도달/오류 시 `LLM_UNAVAILABLE`, 응답 지연 시 `LLM_TIMEOUT`을 5초 내 산출
    - _Requirements: 9.4, 5.7_
    - _의존: 6.1_
  - [ ]* 6.5 [LLM] 프롬프트 구성 속성 테스트
    - **Property 7: 생성 프롬프트는 방의 모든 메시지와 템플릿 지시를 포함한다**
    - **Validates: Requirements 4.3, 9.2**
    - Hypothesis, 최소 100회 반복
    - _의존: 6.2_
  - [ ]* 6.6 [LLM] 응답 파싱 속성 테스트
    - **Property 8: 파싱된 보고서는 네 섹션을 모두 포함한다**
    - **Validates: Requirements 5.2, 9.3**
    - Hypothesis, 최소 100회 반복
    - _의존: 6.3_
  - [ ]* 6.7 [LLM] LLM 오류 경로 단위 테스트
    - LLM 미도달/타임아웃/비정형 응답 등 오류 경로 예시 테스트
    - _Requirements: 5.7, 9.4_
    - _의존: 6.4_

- [ ] 7. [LLM] 체크포인트 — LLM 트랙 단독 검증
  - LLM 트랙의 모든 테스트가 통과하는지 확인한다. 의문점이 있으면 사용자에게 확인한다.

- [ ] 8. [INTEGRATION] 통합 및 패키징
  - [ ] 8.1 [INTEGRATION] 실제 LLMClient를 BE ReportService에 연결
    - stub LLM 클라이언트를 실제 LLMClient(LLM 트랙)로 교체, 원자적 보고서 생성 흐름이 실제 클라이언트로도 성립하는지 확인
    - _Requirements: 5.1, 5.3, 9.1, 9.3, 9.4_
    - _의존: 4.7, 6.1, 6.2, 6.3, 6.4_
  - [ ] 8.2 [INTEGRATION] FE를 실제 BE에 연결
    - mock 백엔드를 실제 루프백(`127.0.0.1:{PORT}`) BE로 전환, apiClient가 실제 응답/오류를 처리하도록 배선
    - _Requirements: 10.3, 10.9_
    - _의존: 3.1, 4.6_
  - [ ] 8.3 [INTEGRATION] pywebview 데스크톱 셸 통합
    - Python 진입점에서 env 검증 → FastAPI 백그라운드 스레드 기동 → 포트 바인딩 확인 → pywebview 창 생성 및 빌드된 React 자산 로드, 시작 실패(env 누락/포트 충돌) 시 셸 오류 창 표시
    - _Requirements: 10.1, 10.2, 10.6, 10.8, 11.6_
    - _의존: 8.1, 8.2_
  - [ ]* 8.4 [INTEGRATION] E2E 보고서 흐름 통합 테스트
    - 메시지 입력 → 보고서 생성 → Closed 전환 → 신규 Active 방 노출까지 전체 흐름 자동 통합 테스트 (LLM은 mock 또는 대표 엔드포인트)
    - _Requirements: 10.7, 11.7_
    - _의존: 8.3_
  - [ ] 8.5 [INTEGRATION] Phase 2 — PyInstaller 단일 실행 파일 패키징
    - React build 정적 자산 + Python 진입점을 PyInstaller로 단일 Windows 실행 파일로 빌드
    - _Requirements: 11.1, 11.5_
    - _의존: 8.3_
  - [ ] 8.6 [INTEGRATION] Phase 2 — Inno Setup 설치 파일 및 라이프사이클
    - Inno Setup으로 Windows Installer 생성, 런치 엔트리 생성, 설치 실패 시 정리, 언인스톨 옵션, 설치 후 LLM 설정값 영속 및 누락 시 보고서 흐름 차단
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.8, 11.9, 11.10_
    - _의존: 8.5_

- [ ] 9. [INTEGRATION] 최종 체크포인트 — 전체 통합 검증
  - 모든 테스트가 통과하는지 확인한다. 의문점이 있으면 사용자에게 확인한다.

## Notes

- `*`로 표시된 하위 작업은 테스트 관련(속성/단위/통합) 작업으로 선택적이며, 빠른 MVP를 위해 건너뛸 수 있다. 핵심 구현 작업은 선택적이지 않다.
- 각 작업은 추적성을 위해 특정 요구사항 절을 참조한다.
- 속성 기반 테스트: Backend/LLM은 Python **Hypothesis**(최소 100회 반복), Frontend는 **fast-check** + React Testing Library를 사용한다.
- **트랙 독립성**: 작업 1(파운데이션) 완료 후 `[FE]`, `[BE]`, `[LLM]` 트랙은 서로 의존하지 않는다. FE는 mock 백엔드, BE는 stub LLM 클라이언트에만 의존하며, 실제 연결은 `[INTEGRATION]` 단계에서 이루어진다.
- 속성 번호(Property 1–13)는 design.md의 Correctness Properties와 일치한다: Property 1–4·6·9–13은 Backend, Property 5는 Frontend, Property 7–8은 LLM 트랙에서 검증한다.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4"] },
    { "id": 2, "tasks": ["1.5"] },
    { "id": 3, "tasks": ["3.1", "4.1", "4.2", "4.3", "6.1", "6.2", "6.3"] },
    { "id": 4, "tasks": ["3.2", "3.3", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9", "4.4", "4.5", "6.4"] },
    { "id": 5, "tasks": ["3.10", "4.6", "4.16", "4.17", "6.5", "6.6", "6.7"] },
    { "id": 6, "tasks": ["3.11", "4.7", "4.8", "4.9", "4.10", "4.11", "4.12", "4.15", "4.18"] },
    { "id": 7, "tasks": ["4.13", "4.14"] },
    { "id": 8, "tasks": ["8.1", "8.2"] },
    { "id": 9, "tasks": ["8.3"] },
    { "id": 10, "tasks": ["8.4", "8.5"] },
    { "id": 11, "tasks": ["8.6"] }
  ]
}
```
