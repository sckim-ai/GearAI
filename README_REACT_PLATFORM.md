# Gear AI React Platform

기존 Streamlit 기반 app.py를 React + Vite 프론트엔드와 FastAPI 백엔드로 구성한 기어 설계 챗 Agent 플랫폼입니다.

## 🏗️ 아키텍처

```
GearAI/
├── backend/                 # FastAPI 백엔드
│   ├── main.py             # FastAPI 메인 서버 + WebSocket
│   ├── api/                # REST API 라우터
│   ├── models/             # Pydantic 데이터 모델
│   └── requirements.txt    # 백엔드 의존성
├── frontend/               # React + Vite 프론트엔드
│   ├── src/
│   │   ├── components/     # React 컴포넌트
│   │   │   ├── Chat/       # 채팅 관련 컴포넌트
│   │   │   ├── Sidebar/    # 사이드바 및 설정
│   │   │   └── Workflow/   # 워크플로우 시각화
│   │   ├── services/       # API 서비스 레이어
│   │   ├── hooks/          # 커스텀 React 훅
│   │   ├── types/          # TypeScript 타입 정의
│   │   └── utils/          # 유틸리티 함수
│   └── package.json        # 프론트엔드 의존성
└── agents/                 # 기존 에이전트 재사용
```

## 🚀 실행 방법

### 1. 간편 실행 (권장)
```bash
# 백엔드와 프론트엔드를 동시에 시작
./start_gear_ai.bat
```

### 2. 개별 실행

#### 백엔드 서버
```bash
cd backend
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 프론트엔드 서버
```bash
cd frontend
npm install
npm run dev
```

## 🌐 접속 정보

- **프론트엔드**: http://localhost:5173
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## ✨ 주요 기능

### 1. 실시간 채팅
- WebSocket 기반 실시간 스트리밍 응답
- 타이핑 인디케이터 및 응답 상태 표시
- 메시지 히스토리 관리

### 2. 에이전트 관리
- 다중 에이전트 지원 (Chatbot, Gear Classifier, Gear Design, Gear Agent)
- 동적 에이전트 변경 및 설정 관리
- 에이전트별 독립적인 대화 세션

### 3. 모델 설정
- LLM 프로바이더 선택 (OpenAI, Anthropic, Google)
- 모델별 설정 (temperature, model selection)
- API 키 상태 확인

### 4. 기어 설계 특화 기능
- 기어 타입 선택 UI (Gear Pair, Three Gear, Planetary 등)
- 워크플로우 시각화 (LangGraph 지원)
- 설계 과정 추적 및 통계

## 🛠️ 기술 스택

### 프론트엔드
- **React 18** + **TypeScript**
- **Vite** (빌드 도구)
- **TailwindCSS** (스타일링)
- **Lucide React** (아이콘)
- **WebSocket** (실시간 통신)

### 백엔드
- **FastAPI** (API 프레임워크)
- **WebSocket** (실시간 통신)
- **Pydantic** (데이터 검증)
- **Uvicorn** (ASGI 서버)

### 공통 의존성
- 기존 에이전트 서비스 재사용
- OpenAI, Anthropic, Google API 지원
- UV 패키지 관리자

## 📊 API 엔드포인트

### REST API
- `GET /api/agents/available` - 사용 가능한 에이전트 목록
- `GET /api/agents/config/{agent_type}` - 에이전트 설정 조회
- `GET /api/agents/workflow/{agent_type}` - 워크플로우 정보
- `GET /api/config/api-keys` - API 키 상태
- `POST /api/config/update` - 설정 업데이트

### WebSocket
- `ws://localhost:8000/ws/{client_id}` - 실시간 채팅 및 상태 동기화

## 🔧 개발 환경 설정

### 환경 변수
`.env` 파일 생성:
```env
OPENAI_API_KEY="your_openai_key"
ANTHROPIC_API_KEY="your_anthropic_key"
GOOGLE_API_KEY="your_google_key"
FIRECRAWL_API_KEY="your_firecrawl_key"
YOUTUBE_API_KEY="your_youtube_key"
```

### 의존성 설치

#### 백엔드
```bash
cd backend
uv sync
uv add fastapi "uvicorn[standard]" websockets pydantic python-multipart
```

#### 프론트엔드
```bash
cd frontend
npm install
npm install @tailwindcss/typography lucide-react autoprefixer @tailwindcss/postcss
```

## 🔄 Streamlit vs React 비교

| 기능 | Streamlit (app.py) | React Platform |
|------|-------------------|----------------|
| 실시간 응답 | st.write + rerun | WebSocket 스트리밍 |
| 상태 관리 | session_state | React State + Context |
| UI 컴포넌트 | Streamlit 위젯 | 커스텀 React 컴포넌트 |
| 스타일링 | 제한적 | TailwindCSS 완전 커스터마이징 |
| 확장성 | 단일 파일 | 모듈화된 컴포넌트 아키텍처 |
| 배포 | Streamlit Cloud | 별도 프론트/백엔드 배포 |

## 🎯 주요 개선 사항

1. **성능**: WebSocket 기반 실시간 통신으로 응답성 향상
2. **UI/UX**: 현대적이고 반응형 사용자 인터페이스
3. **확장성**: 모듈화된 컴포넌트 구조로 유지보수성 증대
4. **타입 안전성**: TypeScript로 런타임 오류 방지
5. **개발 경험**: Hot reload, 디버깅 도구, 코드 분할

## 📝 사용법

1. `start_gear_ai.bat` 실행하여 서버 시작
2. 브라우저에서 http://localhost:5173 접속
3. 우측 사이드바에서 에이전트 및 모델 설정
4. 채팅창에서 기어 설계 요청
5. 기어 옵션 선택 UI 활용
6. 워크플로우 시각화로 진행 상황 확인

## 🔮 향후 계획

- [ ] 채팅 히스토리 영구 저장
- [ ] 다중 사용자 지원
- [ ] 기어 설계 결과 시각화 강화
- [ ] 모바일 반응형 디자인 최적화
- [ ] PWA(Progressive Web App) 지원
- [ ] 실시간 협업 기능

---

**기존 Streamlit app.py 대비 현대적이고 확장 가능한 웹 애플리케이션으로 발전시킨 기어 설계 AI 플랫폼입니다.**