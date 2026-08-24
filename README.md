# FactChat AI Agent Starter Project

사내 FactChat API Gateway를 사용하여 새로운 AI 에이전트를 개발하기 위한 독립된 깔끔한 스타터 템플릿 프로젝트입니다.

## 📂 파일 구조
* `.env`: 사내 FactChat API 인증 및 엔드포인트 설정 파일
* `.gitignore`: Git 관리에서 가상환경 및 `.env`를 제외하기 위한 설정
* `requirements.txt`: 필수 파이썬 의존성 패키지 정의
* `src/main.py`: `gpt-5.4` 및 `claude-sonnet-4-5` 모델 호출을 쉽게 래핑한 클라이언트 예제 파일

---

## 🛠️ 시작하기 및 가상환경 설정

기존 프로젝트 가상환경을 그대로 사용하시거나, 새롭게 독립된 가상환경을 구축해 시작할 수 있습니다.

### 방법 A. 기존 가상환경을 사용해 실행하기 (추천)
현재 상위 디렉토리의 가상환경(`venv`)을 사용해 바로 실행할 수 있습니다.

1. **상위 디렉토리로 가상환경 활성화 (필요한 경우)**:
   ```bash
   source ../venv/bin/activate
   ```
2. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```
3. **테스트 스크립트 실행**:
   ```bash
   python src/main.py
   ```

### 방법 B. 새 가상환경을 만들어 완전히 새로 시작하기
완전히 고립된 프로젝트 환경을 만들고 싶다면 다음과 같이 진행하세요.

1. **새 가상환경 생성**:
   ```bash
   python -m venv venv
   ```
2. **가상환경 활성화**:
   * macOS / Linux:
     ```bash
     source venv/bin/activate
     ```
   * Windows (PowerShell):
     ```bash
     .\venv\Scripts\Activate.ps1
     ```
3. **의존성 설치**:
   ```bash
   pip install -r requirements.txt
   ```
4. **테스트 실행**:
   ```bash
   python src/main.py
   ```

---

## 💡 모델 호출 예시 (`main.py` 사용법)

```python
from src.main import FactChatClient

client = FactChatClient()

# 1. OpenAI 호환 모델 (속도, 정형화 요약 등에 최적화)
gpt_reply = client.ask_gpt("질문 내용", system_prompt="시스템 역할 부여")

# 2. Anthropic 호환 모델 (고난이도 문장 작성, 법률/보안 분석에 최적화)
claude_reply = client.ask_claude("질문 내용", system_prompt="시스템 역할 부여")
```
