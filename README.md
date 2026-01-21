# Microsoft Agent Framework Backend Sample

이 프로젝트는 **Microsoft Agent Framework Backend**를 구성하고 테스트하기 위한 샘플 프로젝트입니다. FastAPI를 기반으로 구축되었으며, AI 에이전트, 스레드, 워크플로우 등을 관리하는 RESTful API를 제공합니다.

## 프로젝트 구조

```
src/
  backend/       # 백엔드 소스 코드 (FastAPI)
    routers/     # API 라우터 (에이전트, 스레드 등)
    main.py      # 애플리케이션 진입점
    models.py    # 데이터 모델
  frontend/      # 프론트엔드 소스 코드 (예정)
tests/           # 테스트 코드
uploads/         # 파일 업로드 디렉토리
```

## 시작하기 (Getting Started)

### 사전 요구 사항 (Prerequisites)

- Python 3.9 이상
- pip

### 설치 (Installation)

1. 리포지토리를 클론하고 프로젝트 루트로 이동합니다.

2. 가상 환경을 생성하고 활성화하는 것을 권장합니다:
   ```bash
   cd /src/backend
   python -m venv .venv
   # Windows
   .\.venv\Scripts\Activate.ps1
 
   ```

3. 필요한 패키지를 설치합니다:
   ```bash
   pip install -r requirements.txt
   ```

## 실행 방법 (Running the App)

프로젝트 루트 디렉토리에서 다음 명령어로 백엔드 서버를 실행합니다:

```bash
uvicorn src.backend.main:app --reload
```

- `--reload`: 코드가 변경되면 서버를 자동으로 재시작합니다 (개발 모드).

서버가 정상적으로 실행되면 터미널에 다음과 같은 로그가 표시됩니다:

```
INFO:     Uvicorn running on http://127.0.0.1:8000
...
Agent Framework API 서버를 시작합니다...
API 문서 (Swagger UI): http://localhost:8000/docs
```

## API 문서 및 기능 (API Documentation)

서버 실행 후 웹 브라우저에서 다음 주소로 접속하여 API 문서를 확인할 수 있습니다.

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 주요 API 엔드포인트 및 활용 (Key Concepts & Usage)

이 시스템의 핵심 흐름은 **"특정 에이전트(Agent)를 대화방(Thread)에 불러와서 실행(Run)시킨다"**는 것입니다.

#### 1. 컴포넌트 간의 관계 (Relationships)

*   **Agents (두뇌 & 도구):** "누가 일할 것인가?"를 정의합니다. 모델(예: GPT-4), 시스템 지시사항(페르소나), 사용할 도구(Tools) 설정을 담고 있습니다.
*   **Threads (기억 & 대화):** "어디서 이야기할 것인가?"를 정의합니다. 사용자와 에이전트 간의 대화 기록(Messages)을 저장하는 상태 공간입니다.
*   **Runs (실행 & 처리):** "작업을 수행해라"라는 명령입니다. 특정 **Thread**의 대화 내용을 바탕으로 특정 **Agent**가 응답을 생성하도록 트리거합니다.
*   **Files (지식 & 데이터):** 에이전트가 분석하거나 참고할 문서입니다.
*   **Workflows (오케스트레이션):** 단순 대화를 넘어, 복잡한 업무 프로세스나 여러 에이전트의 협업을 정의하는 상위 개념입니다.

#### 2. 활용 시나리오 (Usage Scenario)

**예시: "매출 보고서를 분석해주는 AI 비서"**

1.  **준비 (Files & Agents)**:
    *   `Files API`로 `sales_data.csv` 업로드.
    *   `Agents API`로 '데이터 분석가' 에이전트 생성 (지시사항 부여, 파일 연결).
2.  **대화 시작 (Threads)**:
    *   `Threads API`로 새 스레드 생성.
    *   사용자 질문("올해 매출 추세 그려줘")을 메시지로 추가.
3.  **실행 (Runs)**:
    *   `Runs API`로 실행 요청 (Agent + Thread).
    *   에이전트가 내부적으로 파일 분석 및 생각(Thinking) 수행.
4.  **결과 확인**:
    *   `Runs API`로 상태 확인 (`completed` 될 때까지).
    *   `Threads API`로 에이전트가 작성한 답변(메시지) 조회.

#### 3. API별 상세 역할 및 활용

| API 컴포넌트 | 경로 (Prefix) | 역할 및 주요 기능 | 활용 예시 |
| :--- | :--- | :--- | :--- |
| **System** | `/api/v1` | **서버 상태 관리**<br>- 헬스 체크 (`/health`), 버전 정보 | 로드 밸런서 체크 |
| **Files** | `/api/v1/files` | **파일 자산 관리**<br>- 파일 업로드/삭제/목록 | 분석할 CSV 데이터, 검색(RAG)할 PDF 문서 관리 |
| **Agents** | `/api/v1/agents` | **AI 페르소나 정의**<br>- 모델, 프롬프트, 도구 설정 | '코딩 도우미', '고객 상담원' 등 특화 에이전트 생성 |
| **Threads** | `/api/v1/threads` | **대화 맥락 관리**<br>- 스레드 생성, 메시지 관리 | 사용자 세션별 대화방 생성 및 기록 유지 |
| **Runs** | `/api/v1/runs` | **추론 엔진 트리거**<br>- 에이전트 실행 및 모니터링 | 질문에 대한 답변 생성 요청 |
| **Workflows** | `/api/v1/workflows` | **복합 프로세스 관리**<br>- 다단계 작업 정의 | '요약 -> 번역 -> 이메일 발송' 자동화 |

#### 4. UI 개발을 위한 API 호출 순서 (API Flow for UI Development)

웹 프론트엔드에서 **AI 채팅 애플리케이션**을 구현할 때의 상세 API 호출 흐름입니다.

**1. 준비 단계 (Initial Setup)**
사용자가 대화할 대상을 선택하거나 설정하는 단계입니다.
*   **에이전트 목록 조회** (`GET /api/v1/agents`)
    *   화면에 표시할 에이전트 목록을 불러옵니다.
    *   사용자가 특정 에이전트(ID:`agent_123`)를 선택합니다.

**2. 대화 시작 (Session Start)**
사용자가 "새 채팅" 버튼을 눌렀을 때의 동작입니다.
*   **스레드 생성** (`POST /api/v1/threads`)
    *   빈 대화방을 생성하고 `thread_id` (예: `thread_abc123`)를 반환받습니다.
    *   이 ID를 프론트엔드 상태(State)에 저장합니다.

**3. 메시지 교환 루프 (Interaction Loop)**
사용자가 메시지를 입력하고 답변을 받는 핵심 과정입니다.

*   **Step A: 메시지 전송** (`POST /api/v1/threads/{thread_id}/messages`)
    *   사용자가 입력한 텍스트를 스레드에 저장합니다.
    *   Payload: `{ "role": "user", "content": "안녕하세요!" }`
    *   화면에 사용자의 말풍선을 즉시 표시합니다.

*   **Step B: 실행 요청 (Run)** (`POST /api/v1/runs`)
    *   에이전트에게 답변 생성을 요청합니다.
    *   Payload: `{ "agent_id": "agent_123" }`
    *   **응답**: `run_id`와 초기 상태 `queued`를 받습니다.

*   **Step C: 상태 확인 (Polling)** (`GET /api/v1/runs/{run_id}`)
    *   답변 생성이 완료될 때까지 주기적으로(예: 1초 간격) 호출합니다.
    *   `status` 값을 확인합니다:
        *   `queued` / `in_progress`: 계속 대기 (로딩 표시)
        *   `completed`: 완료 -> **다음 단계로 이동**
        *   `failed`: 에러 처리

*   **Step D: 답변 표시** (`GET /api/v1/threads/{thread_id}/messages`)
    *   `completed` 상태가 되면 메시지 목록을 다시 조회합니다.
    *   새로 추가된 `assistant` 역할의 메시지를 화면에 표시합니다.

**요약 흐름도 (Sequence Diagram)**

```mermaid
sequenceDiagram
    participant User as 사용자 (Web UI)
    participant API as 백엔드 API (Backend)

    User->>API: 1. 에이전트 목록 조회 (GET /agents)
    User->>User: 에이전트 선택
    User->>API: 2. 스레드 생성 (POST /threads)
    API-->>User: thread_id 반환

    loop 대화 반복
        User->>API: 3. 메시지 전송 (POST /threads/{id}/messages)
        User->>API: 4. 실행(Run) 요청 (POST /runs)
        API-->>User: run_id 반환

        loop 완료될 때까지 (Polling)
            User->>API: 5. 상태 확인 (GET /runs/{run_id})
            API-->>User: status: "in_progress" -> "completed"
        end

        User->>API: 6. 답변 조회 (GET /threads/{id}/messages)
        API-->>User: 에이전트 답변 반환
        User->>User: 화면 업데이트
    end
```

## 테스트 (Testing)

`pytest`를 사용하여 작성된 테스트 코드를 실행할 수 있습니다:

```bash
pytest
```
