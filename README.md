# CraftServer - Minecraft Server Manager

Crafty Controller와 유사한 Docker 기반 마인크래프트 서버 관리 프로그램입니다. Modrinth 스타일의 현대적이고 깔끔한 웹 인터페이스를 제공합니다.

## 주요 기능

### 서버 관리
- 🚀 서버 시작/중지/재시작
- 📊 실시간 서버 상태 모니터링
- 💻 실시간 콘솔 로그
- ⚙️ 서버 설정 관리

### 모니터링
- 플레이어 수 및 최대 플레이어 수
- 서버 가동 시간
- CPU 및 메모리 사용량
- 서버 상태 표시

### 백업 관리
- 서버 백업 생성
- 백업 복원
- 백업 목록 조회

### 웹 인터페이스
- Modrinth 스타일의 현대적인 다크 테마
- 반응형 디자인 (모바일 지원)
- 실시간 WebSocket 통신
- 직관적인 사용자 인터페이스

## 기술 스택

### Backend
- **FastAPI**: 현대적인 Python 웹 프레임워크
- **WebSocket**: 실시간 콘솔 로그 스트리밍
- **Pydantic**: 데이터 검증 및 설정 관리
- **psutil**: 시스템 모니터링

### Frontend
- **Vanilla JavaScript**: 가볍고 빠른 프론트엔드
- **Modern CSS**: Modrinth 스타일의 디자인
- **WebSocket API**: 실시간 통신

### Infrastructure
- **Docker**: 컨테이너화 (멀티 아키텍처 지원: AMD64, ARM64)
- **Docker Compose**: 간편한 배포
- **Java 21**: 마인크래프트 서버 실행

## 설치 및 실행

### 필요 사항
- Docker
- Docker Compose (선택사항)

### 빠른 시작

#### Docker Hub에서 실행 (권장)

```bash
# Docker Hub에서 이미지 가져오기
docker pull yuchanshin/craftserver:latest

# 컨테이너 실행
docker run -d \
  --name craftserver \
  -p 8000:8000 \
  -p 25565:25565 \
  -v $(pwd)/minecraft:/app/minecraft \
  -v $(pwd)/backups:/app/backups \
  -v $(pwd)/logs:/app/logs \
  -e MINECRAFT_VERSION=1.20.1 \
  -e SERVER_MEMORY=2G \
  -e SERVER_PORT=25565 \
  yuchanshin/craftserver:latest
```

#### Docker Compose로 실행

1. **저장소 클론**
```bash
git clone https://github.com/yuchanshin/craftserver.git
cd craftserver
```

2. **Docker Compose로 실행**
```bash
docker-compose up -d
```

#### 소스코드에서 빌드

```bash
git clone https://github.com/yuchanshin/craftserver.git
cd craftserver
docker build -t craftserver .
docker run -d -p 8000:8000 -p 25565:25565 craftserver
```

### 웹 인터페이스 접속
- 웹 UI: http://localhost:8000
- 마인크래프트 서버: localhost:25565

## Docker Hub

이 프로젝트는 Docker Hub에 게시되어 있습니다:
- **이미지**: `yuchanshin/craftserver`
- **태그**: `latest`, `1.0.0`
- **지원 아키텍처**: AMD64, ARM64

```bash
# 최신 버전
docker pull yuchanshin/craftserver:latest

# 특정 버전
docker pull yuchanshin/craftserver:1.0.0
```

### 환경 변수

`docker-compose.yml`에서 다음 환경 변수를 설정할 수 있습니다:

```yaml
environment:
  - MINECRAFT_VERSION=1.20.1  # 마인크래프트 버전
  - SERVER_MEMORY=2G          # 서버 메모리 할당
  - SERVER_PORT=25565         # 마인크래프트 서버 포트
```

## 디렉토리 구조

```
craftserver/
├── backend/                 # FastAPI 백엔드
│   ├── main.py             # API 엔드포인트
│   ├── minecraft_manager.py # 서버 관리 로직
│   └── models.py           # 데이터 모델
├── frontend/               # 웹 인터페이스
│   ├── index.html          # 메인 HTML
│   └── static/
│       ├── css/
│       │   └── style.css   # Modrinth 스타일
│       └── js/
│           └── app.js      # 프론트엔드 로직
├── minecraft/              # 마인크래프트 서버 파일
├── backups/                # 백업 저장소
├── logs/                   # 로그 파일
├── Dockerfile              # Docker 이미지 빌드
├── docker-compose.yml      # Docker Compose 설정
└── requirements.txt        # Python 의존성
```

## API 엔드포인트

### 서버 제어
- `GET /api/status` - 서버 상태 조회
- `POST /api/server/start` - 서버 시작
- `POST /api/server/stop` - 서버 중지
- `POST /api/server/restart` - 서버 재시작
- `POST /api/server/command` - 콘솔 명령 전송

### 설정 관리
- `GET /api/config` - 서버 설정 조회
- `POST /api/config` - 서버 설정 업데이트

### 백업 관리
- `GET /api/backups` - 백업 목록 조회
- `POST /api/backup` - 백업 생성
- `POST /api/backup/restore` - 백업 복원

### WebSocket
- `WS /ws/console` - 실시간 콘솔 로그

## 사용 방법

### 1. 서버 시작
1. 대시보드에서 "시작" 버튼 클릭
2. 서버가 초기화되고 실행됩니다
3. 상태 표시가 "서버 온라인"으로 변경됩니다

### 2. 콘솔 사용
1. "콘솔" 탭으로 이동
2. 실시간 로그를 확인할 수 있습니다
3. 하단 입력창에서 명령어를 실행할 수 있습니다

### 3. 설정 변경
1. "설정" 탭으로 이동
2. 서버 설정을 수정합니다
3. "설정 저장" 버튼을 클릭합니다
4. 서버를 재시작하여 변경사항을 적용합니다

### 4. 백업 관리
1. "백업" 탭으로 이동
2. "새 백업 생성" 버튼으로 백업을 만듭니다
3. 백업 목록에서 "복원" 버튼으로 백업을 복원할 수 있습니다

## 개발

### 로컬 개발 환경

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker 빌드

```bash
# 로컬 아키텍처용 빌드
docker build -t craftserver .

# 멀티 아키텍처 빌드 (AMD64, ARM64)
docker buildx build --platform linux/amd64,linux/arm64 -t craftserver .

# 컨테이너 실행
docker run -d -p 8000:8000 -p 25565:25565 craftserver
```

## 보안 고려사항

- 프로덕션 환경에서는 인증 시스템을 추가하는 것을 권장합니다
- 환경 변수로 민감한 정보를 관리하세요
- 방화벽 규칙을 적절히 설정하세요
- HTTPS를 사용하여 웹 인터페이스를 보호하세요

## 문제 해결

### 서버가 시작되지 않는 경우
- 메모리 할당이 충분한지 확인
- Java가 올바르게 설치되었는지 확인
- 로그 파일을 확인하여 오류 메시지 확인

### 포트 충돌
- 8000번 또는 25565번 포트가 이미 사용 중인지 확인
- `docker-compose.yml`에서 포트를 변경

### 백업 복원 실패
- 충분한 디스크 공간이 있는지 확인
- 백업 파일이 손상되지 않았는지 확인

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 기여

버그 리포트와 기능 요청은 GitHub Issues를 통해 제출해 주세요.

## 감사의 말

- Modrinth - UI/UX 디자인 영감
- Crafty Controller - 기능 아이디어
- Minecraft 커뮤니티
