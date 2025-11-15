# CraftServer 에이전트 가이드라인

## 빌드 및 실행 명령어
- **개발 서버**: `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
- **Docker 빌드**: `docker build -t craftserver .`
- **Docker 실행**: `docker-compose up -d`
- **의존성 설치**: `pip install -r requirements.txt`

## 테스트
- 현재 테스트 프레임워크 미설정. pytest 추가 필요.

## 코드 스타일

### Python 백엔드
- **Import**: 표준 라이브러리, 서드파티(FastAPI, Pydantic), 로컬 모듈 순으로 그룹화
- **타입**: 데이터 검증에 Pydantic 모델 사용; 모든 함수에 타입 힌트 적용
- **비동기**: I/O 작업은 async/await 사용; 메서드는 `async def`로 시작
- **모델**: `models.py`에서 Pydantic BaseModel로 정의
- **네이밍**: 함수/변수는 snake_case, 클래스는 PascalCase
- **에러 처리**: 상태 코드와 상세 메시지를 포함한 HTTPException 발생
- **엔드포인트**: `/api/{리소스}/{액션}` 패턴과 적절한 HTTP 동사 사용

### 프론트엔드 (Vanilla JS)
- **클래스**: 앱 구조에 ES6 클래스 사용
- **네이밍**: JS 변수/함수는 camelCase
- **API 호출**: fetch API와 async/await 사용
- **WebSocket**: 실시간 업데이트(콘솔 로그, 메트릭)에 사용
