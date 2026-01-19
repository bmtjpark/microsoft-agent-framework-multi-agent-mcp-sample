# Microsoft Agent Framework SDK 테스트 프로젝트

이 프로젝트는 **Microsoft Agent Framework** (Python SDK)를 테스트하기 위한 프로젝트입니다. 
이미 배포된 Azure AI Foundry 환경을 사용하며, 환경 설정 정보는 `.env` 파일을 통해 관리됩니다.

참조: [Microsoft Agent Framework GitHub](https://github.com/microsoft/agent-framework)

## 사전 요구 사항

- **Python 3.10+**: [Python 설치](https://www.python.org/downloads/)
- **Azure Developer CLI (`azd`)**: [`azd` 설치](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- **VS Code** 및 **Polyglot Notebooks** 또는 **Jupyter** 확장 프로그램.

## 설정

이 프로젝트는 이미 배포된 Azure 리소스를 사용합니다. `src/.env` 파일에 필요한 환경 변수가 설정되어 있어야 합니다.

**필수 `src/.env` 변수:**
- `AZURE_AI_SERVICE_NAME` 또는 `AZURE_OPENAI_ENDPOINT`: Azure OpenAI 서비스 이름 또는 엔드포인트 URL
- `AZURE_OPENAI_DEPLOYMENT_NAME`: (선택 사항) 모델 배포 이름 (기본값: `gpt-4o-mini`)
- `AZURE_AI_PROJECT_CONNECTION_STRING`: (선택 사항) Azure AI Project 연결 문자열 (Telemetry 연결용)
- `AZURE_SEARCH_ENDPOINT`: (선택 사항) Azure AI Search 엔드포인트 (Vector Store/검색 연동용)
- `AZURE_TENANT_ID`: Azure 테넌트 ID
- `AZURE_SUBSCRIPTION_ID`: Azure 구독 ID
- `AZURE_RESOURCE_GROUP`: 리소스 그룹 이름

## 실행 방법

1.  **환경 구성 및 로그인**:
    `src` 폴더로 이동하여 가상 환경을 생성하고 활성화한 후, Azure에 로그인하고 필요한 패키지를 설치합니다.

    ```pwsh
    cd src
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1  # Windows
    # source .venv/bin/activate   # Mac/Linux

    # 패키지 설치
    pip install agent-framework --pre azure-identity python-dotenv azure-ai-projects azure-monitor-opentelemetry azure-search-documents azure-storage-blob openai ipykernel 
    
    # Azure 로그인 (Local Auth)
    azd auth login --use-device-code

    ```

2.  **노트북 실행**:
    - VS Code에서 `src/microsoft-agent-framework.ipynb` 파일을 엽니다.
    - **커널 선택 (Select Kernel)**을 클릭하고, 위에서 생성한 `.venv` (Python 환경)를 선택합니다.
    - 노트북의 셀을 순차적으로 실행하여 SDK 기능을 테스트합니다.

## 테스트 시나리오 (Notebook 예제)

이 노트북(`microsoft-agent-framework.ipynb`)은 다음과 같은 단계별 예제를 포함합니다:

1.  **환경 설정 (Environment Setup)**
    - `.env` 파일 로드 및 Azure OpenAI / Azure AI Project 연결 설정.
2.  **Telemetry 및 Project Client 설정 ([Advanced])**
    - `AIProjectClient`를 사용하여 프로젝트에 연결하고 Application Insights Tracing 활성화.
3.  **기본 에이전트 (Basic Agent - Stateless)**
    - `AzureOpenAIResponsesClient`를 사용한 상태 비저장(Stateless) 수필/시 작성 봇.
4.  **Azure AI Search 통합 ([Advanced])**
    - Azure AI Search 서비스 연결 확인 및 인덱스 조회.
5.  **프로젝트 리소스 확인**
    - AI Project에 연결된 리소스(Connections) 목록 조회.
6.  **Managed Agent (Stateful - [Intermediate])**
    - `AgentsClient`를 사용하여 상태를 관리하는(Stateful) 에이전트 생성 및 대화 실행 (스레드 관리).
    - 예제: 우주 상식 챗봇.
7.  **Managed Agent - Code Interpreter ([Advanced])**
    - 코드 인터프리터 도구를 사용하여 Python 코드를 실행하고 수학 문제를 해결하는 에이전트.
    - 예제: 피보나치 수열 계산 수학자 (Python 코드 실행).
8.  **Managed Agent - RAG (Azure AI Search) ([Advanced])**
    - Azure AI Search를 지식 베이스로 활용하는 검색 기반 에이전트 (RAG).
9.  **멀티 에이전트 오케스트레이션 (Multi-Agent Orchestration - [Advanced])**
    - Python 코드로 워크플로우를 제어하여 여러 에이전트가 협업하는 시나리오.
    - 예제: 신규 입사자 온보딩 계획 수립 (HR 담당자 ↔ 부서 리드 간의 피드백 루프).

