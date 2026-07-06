# Requirements Document

## Introduction

카카오톡 데스크톱 클라이언트와 같이, 자체 애플리케이션 창(native desktop window)을 갖는 단일 독립 실행형 데스크톱 애플리케이션(standalone desktop application)이다. 웹 브라우저에서 URL로 접속하는 브라우저 기반 웹 앱이 아니라, 사용자가 하나의 앱을 실행하면 카카오톡 스타일의 채팅 UI가 표시되는 네이티브 데스크톱 창이 열린다. 사용자는 별도의 로그인 없이 자유롭게 채팅 메시지를 남기고, '주간보고 생성' 버튼을 클릭하면 LLM이 채팅 내용을 분석하여 구조화된 주간보고서를 생성해준다. 보고서가 생성되면 해당 채팅방은 종료되고 새로운 채팅방이 자동 생성된다. 내부적으로 프론트엔드는 React + TypeScript, 백엔드는 Python(FastAPI)로 구성되지만, 사용자에게는 브라우저 탭이 아닌 하나의 통합된 데스크톱 애플리케이션 창으로 제공된다.

본 프로젝트는 두 단계의 전달(delivery) 모델로 진행되며, 두 단계 모두 최종 형태는 단일 데스크톱 애플리케이션 창이다.

- **1차 완료(Phase 1)**: 개발자 PC에서 데스크톱 애플리케이션을 로컬로 실행하여, 브라우저 URL이 아닌 하나의 데스크톱 앱 창으로 전체 기능을 검증할 수 있는 단계이다. 내부적으로 Frontend와 Backend를 함께 구동하되 사용자에게는 하나의 데스크톱 창으로 제공된다.
- **2차 완료(Phase 2)**: 이 데스크톱 애플리케이션을 설치 파일(installer)로 패키징하여, 개발 환경 구성 없이 일반 사용자의 개인 PC(Windows)에 설치하고 하나의 데스크톱 앱으로 실행할 수 있도록 배포하는 단계이다.

## Glossary

- **Desktop_App**: 자체 네이티브 애플리케이션 창을 갖는 단일 독립 실행형 데스크톱 애플리케이션. 카카오톡 데스크톱 클라이언트와 같이 사용자가 실행하면 하나의 앱 창이 열린다. 내부적으로 Frontend와 Backend를 포함하지만 사용자에게는 하나의 통합된 앱으로 제공된다.
- **Application_Window**: Desktop_App이 실행될 때 열리는 네이티브 데스크톱 애플리케이션 창. 웹 브라우저 탭이 아니며, Chat_UI가 이 창 안에 표시된다.
- **Chat_UI**: 카카오톡 데스크톱 스타일의 채팅 인터페이스. Application_Window 내부에 표시되며 메시지 버블, 타임스탬프, 프로필 아이콘 등을 포함한다.
- **User**: 채팅을 통해 주간 보고서를 작성하는 사람.
- **Weekly_Report**: 사용자의 채팅 내용을 LLM이 분석하여 생성하는 구조화된 주간 업무 보고서.
- **Chat_Room**: 하나의 주간 보고서 작성을 위한 채팅 공간. 보고서 생성 시 종료(closed) 상태가 된다.
- **Message**: 채팅 내에서 User가 전송하는 하나의 텍스트 단위.
- **LLM_Service**: 사용자 채팅 내용을 분석하여 구조화된 주간보고서를 생성하는 대형 언어 모델 서비스.
- **Report_Template**: 주간 보고서의 출력 형식을 정의하는 구조. 금주 업무, 차주 계획, 이슈 및 건의사항 등의 섹션을 포함한다.
- **Frontend**: React + TypeScript로 구성된 UI 계층. Desktop_App의 내부 구성 요소이며, 웹 브라우저가 아닌 Application_Window 안에 렌더링된다.
- **Backend**: Python(FastAPI) 기반으로 API 요청을 처리하고 LLM 연동 및 보고서 생성 로직을 담당하는 서버 계층. Desktop_App의 내부 구성 요소로서 Frontend와 함께 하나의 앱으로 패키징·구동된다.
- **Active_Chat_Room**: 현재 메시지 입력이 가능한 열려있는 상태의 Chat_Room.
- **Closed_Chat_Room**: 보고서가 생성되어 더 이상 메시지 입력이 불가한 종료된 Chat_Room.
- **Phase_1_Delivery**: 개발자 PC에서 Frontend와 Backend를 로컬로 실행하여 전체 기능을 검증하는 1차 완료 단계.
- **Phase_2_Delivery**: 애플리케이션을 설치 파일로 패키징하여 개인 PC에 설치·실행할 수 있도록 배포하는 2차 완료 단계.
- **Local_Runtime**: 개발자 PC에서 Desktop_App을 로컬로 구동하는 실행 환경. 내부의 Frontend와 Backend를 함께 구동하여 하나의 Application_Window로 제공한다.
- **Installer**: 개인 PC(Windows)에 Desktop_App을 설치하기 위한 배포용 설치 파일.
- **Installed_Application**: Installer를 통해 개인 PC에 설치되어 실행되는 Desktop_App 인스턴스.

## Requirements

### Requirement 1: 채팅방 접속 및 초기화

**User Story:** As a User, I want to 데스크톱 앱 실행 즉시 채팅방을 사용할 수 있기를, so that 별도의 로그인이나 설정 없이 바로 업무 내용을 기록할 수 있다.

#### Acceptance Criteria

1. WHEN the User launches the Desktop_App, THE Desktop_App SHALL open the Application_Window and display an Active_Chat_Room in the Chat_UI within 2 seconds
2. THE Chat_UI SHALL render within the Application_Window without requiring any authentication or login step
3. WHEN the User launches the Desktop_App for the first time, THE Backend SHALL create a new Chat_Room and return a room identifier
4. WHEN an Active_Chat_Room already exists, THE Chat_UI SHALL display the existing Active_Chat_Room with its previous messages

### Requirement 2: 카카오톡 스타일 채팅 UI

**User Story:** As a User, I want to 카카오톡 데스크톱 클라이언트와 유사한 친숙한 채팅 UI를 데스크톱 앱 창에서 사용하기를, so that 직관적으로 업무 내용을 기록할 수 있다.

#### Acceptance Criteria

1. THE Chat_UI SHALL display User messages as right-aligned message bubbles with a distinct background color
2. THE Chat_UI SHALL display system-generated messages (Weekly_Report) as left-aligned message bubbles with a different background color
3. THE Chat_UI SHALL display a timestamp next to each Message
4. THE Chat_UI SHALL provide a text input field at the bottom of the Application_Window with a send button
5. WHEN a new Message is added, THE Chat_UI SHALL automatically scroll to the latest Message
6. WHEN the User resizes the Application_Window, THE Chat_UI SHALL adapt its layout to the resized Application_Window dimensions

### Requirement 3: 자유 채팅 메시지 입력

**User Story:** As a User, I want to 형식에 구애받지 않고 자유롭게 업무 내용을 채팅으로 남기기를, so that 생각나는 대로 편하게 주간 업무를 기록할 수 있다.

#### Acceptance Criteria

1. WHEN the User types a message and presses the send button or Enter key, THE Frontend SHALL send the Message to the Backend and display it in the Chat_Room
2. WHILE the Chat_Room is in Active state, THE Chat_UI SHALL allow the User to send unlimited messages
3. WHEN the User sends an empty message, THE Frontend SHALL prevent the message from being sent and display no error
4. THE Backend SHALL store all messages within a Chat_Room in chronological order
5. WHEN the User sends a message, THE Backend SHALL persist the message and return a success response within 1 second

### Requirement 4: 주간보고 생성 요청

**User Story:** As a User, I want to '주간보고 생성' 버튼을 클릭하여 보고서를 생성하기를, so that 내가 남긴 채팅 내용을 기반으로 구조화된 주간보고서를 받을 수 있다.

#### Acceptance Criteria

1. WHILE the Chat_Room is in Active state, THE Chat_UI SHALL display a '주간보고 생성' button accessible to the User
2. WHEN the User clicks the '주간보고 생성' button, THE Frontend SHALL send a report generation request to the Backend
3. WHEN the Backend receives a report generation request, THE Backend SHALL send all messages in the Chat_Room to the LLM_Service for analysis
4. WHEN the User clicks the '주간보고 생성' button, THE Chat_UI SHALL display a loading indicator until the report is generated
5. IF the Chat_Room contains no messages, THEN THE Frontend SHALL prevent report generation and display a notification that messages are required

### Requirement 5: LLM 기반 주간보고서 생성

**User Story:** As a User, I want to LLM이 내 채팅 내용을 분석하여 보고서를 만들어주기를, so that 별도의 정리 없이도 잘 구조화된 주간보고서를 얻을 수 있다.

#### Acceptance Criteria

1. WHEN the LLM_Service receives chat messages, THE LLM_Service SHALL analyze the content and generate a structured Weekly_Report
2. THE Weekly_Report SHALL contain the following sections: 작성일, 금주 업무 실적, 차주 업무 계획, 이슈 및 건의사항
3. WHEN the LLM_Service generates the Weekly_Report, THE Backend SHALL return the report to the Frontend within 30 seconds
4. WHEN the Weekly_Report is generated, THE Chat_UI SHALL display the report as a formatted message within the Chat_Room
5. WHEN the Weekly_Report is displayed, THE Chat_UI SHALL provide a copy button to copy the report content to clipboard
6. WHEN the User clicks the copy button, THE Frontend SHALL copy the report text to the system clipboard and display a success notification
7. IF the LLM_Service fails to generate a report, THEN THE Backend SHALL return an error response and THE Chat_UI SHALL display an error message to the User

### Requirement 6: 채팅방 라이프사이클 관리

**User Story:** As a User, I want to 보고서 생성 후 채팅방이 자동으로 정리되고 새 채팅방이 열리기를, so that 다음 주 보고서를 새롭게 작성할 수 있다.

#### Acceptance Criteria

1. WHEN the Weekly_Report is successfully generated, THE Backend SHALL change the Chat_Room status from Active to Closed
2. WHEN the Chat_Room status changes to Closed, THE Chat_UI SHALL disable the text input field and send button for that Chat_Room
3. WHEN the Chat_Room status changes to Closed, THE Backend SHALL automatically create a new Active_Chat_Room
4. WHEN a new Active_Chat_Room is created after report generation, THE Chat_UI SHALL display the new Chat_Room alongside the Closed_Chat_Room
5. THE Chat_UI SHALL allow the User to view Closed_Chat_Room messages and the generated Weekly_Report in read-only mode
6. WHILE the Chat_Room is in Closed state, THE Chat_UI SHALL prevent any message input or report generation for that Chat_Room

### Requirement 7: 채팅방 목록 및 탐색

**User Story:** As a User, I want to 이전 채팅방과 현재 채팅방을 탐색할 수 있기를, so that 이전에 생성한 보고서를 다시 확인할 수 있다.

#### Acceptance Criteria

1. THE Chat_UI SHALL display a list of Chat_Rooms including both Active and Closed Chat_Rooms
2. THE Chat_UI SHALL visually distinguish Active_Chat_Room from Closed_Chat_Rooms in the list
3. WHEN the User selects a Chat_Room from the list, THE Chat_UI SHALL display the messages and report of that Chat_Room
4. THE Chat_UI SHALL display the most recent Active_Chat_Room by default when the application is loaded

### Requirement 8: 백엔드 API

**User Story:** As a Developer, I want to Python FastAPI 기반의 REST API를 제공하기를, so that Frontend와 Backend 간의 통신이 원활하게 이루어진다.

#### Acceptance Criteria

1. THE Backend SHALL be implemented using Python with the FastAPI framework
2. THE Backend SHALL expose a POST endpoint for creating a new Chat_Room
3. THE Backend SHALL expose a POST endpoint for sending a User Message to a Chat_Room
4. THE Backend SHALL expose a GET endpoint for retrieving all messages in a Chat_Room
5. THE Backend SHALL expose a POST endpoint for requesting Weekly_Report generation from a Chat_Room
6. THE Backend SHALL expose a GET endpoint for retrieving the list of Chat_Rooms
7. WHEN the Backend receives a request with an invalid room identifier, THE Backend SHALL return an error response with a descriptive message
8. IF the Backend encounters an internal error, THEN THE Backend SHALL return a structured error response with an error code and message

### Requirement 9: LLM 서비스 연동

**User Story:** As a Developer, I want to LLM API를 연동하여 보고서를 생성하기를, so that 사용자 채팅 내용을 자동으로 분석하고 구조화할 수 있다.

#### Acceptance Criteria

1. THE Backend SHALL integrate with an LLM API to process chat messages and generate reports
2. THE Backend SHALL send a structured prompt to the LLM_Service containing the User messages and Report_Template instructions
3. WHEN the LLM_Service returns a response, THE Backend SHALL parse the response into the Weekly_Report format
4. IF the LLM API is unavailable or returns an error, THEN THE Backend SHALL return a descriptive error to the Frontend within 5 seconds
5. THE Backend SHALL configure the LLM API connection through environment variables for API key and endpoint

### Requirement 10: 1차 완료 — 로컬 실행

**User Story:** As a Developer, I want to 개발자 PC에서 Desktop_App을 로컬로 실행하기를, so that 별도 배포 없이 하나의 데스크톱 앱 창으로 전체 기능을 통합 검증할 수 있다.

#### Acceptance Criteria

1. THE Local_Runtime SHALL run the Desktop_App on a single developer PC as a desktop application that opens its own Application_Window, launching the internal Frontend and Backend together as part of the same Desktop_App
2. WHEN the Developer starts the Local_Runtime, THE Desktop_App SHALL open the Application_Window and display the Chat_UI within 10 seconds after the documented start commands complete, without the Developer opening any web browser or localhost URL
3. WHEN the Frontend sends an API request within the running Desktop_App, THE Backend SHALL respond through a local interface without requiring any external network connection other than the LLM API
4. THE Phase_1_Delivery SHALL provide documented commands to start the Desktop_App, which launches the internal Frontend and Backend together, on the developer PC
5. THE Phase_1_Delivery SHALL provide documented configuration steps for setting the LLM API key and endpoint environment variables before startup
6. IF a required environment variable for the LLM API connection (API key or endpoint) is missing or empty when the Backend starts, THEN THE Backend SHALL halt startup and output a startup error message identifying each missing variable by name
7. WHEN the Local_Runtime is running, THE Local_Runtime SHALL support the complete report generation flow from Message input in the Chat_UI to Weekly_Report display in the Chat_UI within the Application_Window without a manual restart of the Desktop_App
8. IF the Backend cannot bind to its configured local port because the port is already in use when the Backend starts, THEN THE Backend SHALL halt startup and output an error message identifying the conflicting port
9. IF the Frontend cannot reach the Backend within the running Desktop_App, THEN THE Chat_UI SHALL display an error message in the Application_Window indicating that the Backend connection is unavailable

### Requirement 11: 2차 완료 — 설치 파일 패키징 및 배포

**User Story:** As a User, I want to 개발 환경 구성 없이 설치 파일로 데스크톱 애플리케이션을 개인 PC에 설치하기를, so that 개발 지식 없이도 하나의 데스크톱 앱으로 주간보고 애플리케이션을 사용할 수 있다.

#### Acceptance Criteria

1. THE Phase_2_Delivery SHALL package the Desktop_App, including its internal Frontend and Backend, into a single standalone Installer for a Windows personal PC
2. WHEN the User runs the Installer on a Windows personal PC, THE Installer SHALL install the Installed_Application such that the User can start it from the launch entry without installing or configuring any separate development tools, runtimes, or dependencies
3. WHEN the installation completes, THE Installer SHALL create a launch entry that allows the User to start the Installed_Application as a standalone desktop application
4. IF the installation fails to complete, THEN THE Installer SHALL display a descriptive message identifying the failure and SHALL not leave a usable launch entry on the personal PC
5. WHEN the User starts the Installed_Application, THE Installed_Application SHALL launch its internal Frontend and Backend together and open the Application_Window displaying the Chat_UI within 60 seconds, without opening any web browser
6. IF the internal Frontend or Backend fails to start within 60 seconds when the User starts the Installed_Application, THEN THE Installed_Application SHALL display a descriptive message identifying which component failed to start
7. THE Installed_Application SHALL provide the full report generation flow from message input to Weekly_Report display within the Application_Window without requiring separate developer commands
8. WHEN the User configures the LLM API key and endpoint after installation, THE Installed_Application SHALL persist the configured values so that they remain available across restarts of the Installed_Application
9. IF a required LLM API configuration value is missing when the User starts the Installed_Application, THEN THE Installed_Application SHALL display a descriptive message identifying the missing configuration value and SHALL block the report generation flow until the missing value is provided
10. WHERE the User chooses to remove the Installed_Application, THE Installer SHALL provide an uninstall option that removes the Installed_Application and its launch entry from the personal PC
