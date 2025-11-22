# Docker 데이터 복원 계획 (2025-10-27)

## 상황 분석

### 현재 상태:
- Docker Desktop이 F드라이브로 이동됨
- 새로운 빈 Docker 볼륨이 F드라이브에 생성됨 (21GB)
- C드라이브에 이전 데이터 여전히 존재 (39GB docker_data.vhdx)
- 이전 데이터에 10월23일~27일의 모든 주가/지표 데이터 포함

### 문제:
- Docker Desktop이 F드라이브로 이동되었으므로 C드라이브의 이전 데이터에 직접 접근 불가
- 단순 파일 복사는 시간이 오래 걸림 (39GB)

## 해결책: 데이터 추출 및 복원

### 방법 1 (가장 빠름): PostgreSQL Dump/Restore
1. C드라이브의 docker-desktop 배포판을 임시로 등록
2. 이전 PostgreSQL 컨테이너에서 pg_dump로 데이터 추출
3. 새 PostgreSQL 데이터베이스에 복원

### 방법 2 (대체안): WSL 배포판 교환
1. C드라이브의 docker_data.vhdx를 F드라이브로 완전 복사 (시간 오래 걸림)
2. Docker Desktop 설정에서 새 vhdx 파일 지정
3. 기존 데이터 사용

## 현재 진행 상황:
- 파일 복사 시작 (배경에서 실행 중)
- 복사 완료 예상: ~10-15분

## 다음 단계:
- 복사 완료 후 데이터 복원 진행
