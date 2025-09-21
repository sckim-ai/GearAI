# 🔧 Gear AI Platform 문제 해결 가이드

## 연결 오류 해결 방법

### 1. 단계별 실행 (권장)

```bash
# 방법 1: 단계별 스크립트 사용
./start_step_by_step.bat

# 방법 2: 수동 실행
# 터미널 1
cd backend
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# 터미널 2
cd frontend
npm run dev
```

### 2. 일반적인 문제들

#### ❌ 백엔드 서버가 시작되지 않음
**증상**: `ModuleNotFoundError` 또는 import 오류
**해결**:
```bash
cd backend
uv sync
uv add fastapi "uvicorn[standard]" websockets pydantic
```

#### ❌ 프론트엔드가 빌드되지 않음
**증상**: TypeScript 또는 CSS 오류
**해결**:
```bash
cd frontend
npm install
npm install autoprefixer @tailwindcss/postcss
npm run build
```

#### ❌ API 연결 실패
**증상**: 브라우저에서 "연결 오류" 표시
**해결**:
1. 백엔드가 실행 중인지 확인: http://127.0.0.1:8000
2. CORS 설정 확인 (이미 설정됨)
3. 방화벽 설정 확인

#### ❌ WebSocket 연결 실패
**증상**: 실시간 채팅이 작동하지 않음
**해결**:
1. 백엔드에서 WebSocket 엔드포인트 확인
2. 프론트엔드에서 올바른 WebSocket URL 사용 확인
3. 브라우저 개발자 도구에서 WebSocket 연결 상태 확인

### 3. 연결 테스트

```bash
# 연결 상태 확인
./test_connection.bat

# 수동 테스트
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/api/agents/available
```

### 4. 브라우저 개발자 도구 확인

1. **F12** 키로 개발자 도구 열기
2. **Console** 탭에서 JavaScript 오류 확인
3. **Network** 탭에서 API 호출 상태 확인
4. **Application/Storage** 탭에서 WebSocket 연결 상태 확인

### 5. 포트 충돌 해결

```bash
# 포트 사용 중인 프로세스 확인
netstat -ano | findstr :8000
netstat -ano | findstr :5173

# 프로세스 종료 (PID 확인 후)
taskkill /PID [PID번호] /F
```

### 6. 환경 변수 설정

`.env` 파일 생성:
```env
OPENAI_API_KEY="your_openai_key"
ANTHROPIC_API_KEY="your_anthropic_key"
GOOGLE_API_KEY="your_google_key"
```

### 7. 로그 확인

**백엔드 로그**:
- 터미널에서 uvicorn 출력 확인
- Import 오류, API 오류 등 확인

**프론트엔드 로그**:
- 브라우저 Console 탭 확인
- Network 탭에서 실패한 요청 확인

### 8. 완전 초기화

```bash
# 백엔드 의존성 재설치
cd backend
uv sync --reinstall

# 프론트엔드 의존성 재설치
cd frontend
rm -rf node_modules package-lock.json
npm install

# 캐시 정리
npm run build
```

## 🚀 성공적인 실행 확인

✅ 백엔드: http://127.0.0.1:8000 접속 시 `{"message":"Gear AI Backend API","version":"1.0.0"}` 응답
✅ 프론트엔드: http://localhost:5173 접속 시 React 앱 로딩
✅ API: http://127.0.0.1:8000/docs 에서 Swagger 문서 확인
✅ WebSocket: 채팅 입력 시 실시간 응답

## 💡 추가 도움말

문제가 계속 발생하면:
1. `test_connection.bat` 실행하여 상태 확인
2. 브라우저 개발자 도구 Console 오류 메시지 확인
3. 백엔드/프론트엔드 터미널 오류 메시지 확인
4. 환경 변수 및 API 키 설정 확인