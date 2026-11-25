# FRAME 백엔드 실행 및 데모

## 1. 실행

PowerShell에서 `group_proj` 폴더로 이동한 뒤 Python 3.11 이상과 MySQL을 사용합니다. 프로젝트 루트의 `.env`에 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SESSION_SECRET`을 설정합니다. 기존 MySQL에 다섯 테이블이 있으면 해당 DB 이름으로 바로 실행할 수 있습니다.

```powershell
python -m pip install -r requirements-backend.txt
python -m uvicorn backend.main:app --reload
```

다른 PowerShell에서 연결을 확인하고 로그인 화면을 엽니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Start-Process http://127.0.0.1:8000/login
```

`mode`는 `backend`, 연결이 성공하면 `mysql_connected`는 `True`입니다.

## 2. 별도 데모 DB에 샘플 추가

이미 사용 중인 DB와 분리하려면 빈 `frame_demo`를 생성하고 DDL과 시드를 한 번 적용합니다. 예시의 `root`는 데이터베이스 및 테이블을 만들 수 있는 계정으로 바꿔도 됩니다. 각 명령은 비밀번호를 대화형으로 입력받습니다.

```powershell
mysql -u root -p -e "CREATE DATABASE frame_demo CHARACTER SET utf8mb4"
mysql -u root -p --default-character-set=utf8mb4 frame_demo -e "source sql/schema.sql"
mysql -u root -p --default-character-set=utf8mb4 frame_demo -e "source sql/seed.sql"
```

데모 서버를 시작할 PowerShell에서만 DB를 선택합니다.

```powershell
$env:DB_NAME = 'frame_demo'
python -m uvicorn backend.main:app --reload
```

`demo_jineon`, `demo_alice`, `demo_mina`의 데모 비밀번호는 모두 `frame-demo-2026`입니다.

1. `demo_jineon`으로 로그인해 내 사진과 `demo_alice`의 사진이 최신순으로 나오는지 확인합니다.
2. ID 검색에서 `demo_mina`를 찾고 팔로우한 뒤 홈 피드에서 미나의 사진을 확인합니다.
3. 사진을 올리고, 댓글에 `@demo_alice`를 넣은 뒤 좋아요 추가·취소를 보여줍니다.
4. 팔로워·팔로잉 목록과 비밀번호 변경을 확인합니다.

## 3. 테스트

```powershell
python -m unittest discover -s tests -v
$env:FRAME_TEST_MYSQL = '1'
python -m unittest discover -s tests -v
Remove-Item Env:FRAME_TEST_MYSQL
```

두 번째 실행에서는 설정된 MySQL 계정으로 임의 이름의 테스트 DB를 생성하고 `schema.sql`, `seed.sql`을 적용합니다. 테스트 종료 시 생성한 DB를 삭제하므로 테스트 계정에는 DB 생성·삭제와 TRIGGER 권한이 필요합니다.
