# MealFit 1단계 API 테스트

## 1. 환경 변수 준비

`.env.example`을 `.env`로 복사한 뒤 Supabase DB 접속 정보와 JWT 비밀키를 입력합니다.

## 2. 자동 테스트

```powershell
./gradlew.bat test
```

테스트는 Supabase 데이터를 변경하지 않고 메모리 DB를 사용합니다.

## 3. 서버 실행

```powershell
./gradlew.bat bootRun
```

## 4. 수동 호출 순서

```http
GET /api/health
GET /api/health/db
POST /api/auth/signup
POST /api/auth/login
GET /api/auth/me
POST /api/facilities
GET /api/facilities/me
PATCH /api/facilities/me
POST /api/auth/logout
```

로그인 응답의 `accessToken`을 보호 API 요청 헤더에 넣습니다.

```text
Authorization: Bearer {accessToken}
```

현재 로그아웃은 무상태 JWT 방식이므로 프런트엔드가 저장한 토큰을 삭제합니다.
