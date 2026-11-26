# FRAME 백엔드 실행 및 사용 안내

## 1. 실행

PowerShell에서 `group_proj` 폴더로 이동한 뒤 Python 3.11 이상과 MySQL을 사용합니다. 프로젝트 루트의 `.env`에 `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SESSION_SECRET`을 설정합니다. 이미 다섯 테이블이 있는 DB를 사용한다면 `DB_NAME`을 해당 이름으로 설정합니다.

처음 설치하는 경우 아래 예시처럼 빈 DB를 만들고 스키마를 한 번 적용합니다. 예시에서는 `DB_NAME=frame`을 사용하며, `root`는 DB와 테이블을 만들 수 있는 MySQL 계정으로 바꿔도 됩니다.

```powershell
mysql -u root -p -e "CREATE DATABASE frame CHARACTER SET utf8mb4"
mysql -u root -p --default-character-set=utf8mb4 frame -e "source sql/schema.sql"
```

서버를 실행합니다.

```powershell
python -m pip install -r requirements-backend.txt
python -m uvicorn backend.main:app --reload
```

다른 PowerShell에서 DB 연결을 확인하고 로그인 화면을 엽니다.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Start-Process http://127.0.0.1:8000/login
```

`mode`는 `backend`, 연결이 성공하면 `mysql_connected`는 `True`입니다.

## 2. 서비스 사용

1. 로그인 화면에서 **새 계정 만들기**를 선택하고 아이디, 표시 이름, 비밀번호를 입력합니다. 가입 완료 안내가 나오면 만든 계정으로 로그인합니다.
2. **새 게시물**에서 사진과 캡션을 등록하고, 내 프로필과 홈 피드에서 게시물을 확인합니다.
3. **ID 검색**에서 다른 사용자를 찾아 프로필을 열고 팔로우합니다. 홈 피드에는 내 게시물과 팔로우한 사용자의 게시물이 최신순으로 표시됩니다.
4. 게시물에 좋아요를 누르거나 댓글을 작성합니다. 다른 사용자를 언급하려면 댓글에 `@아이디`를 입력합니다.
5. 내 프로필에서 **프로필 사진 변경**을 선택할 수 있습니다. **계정 설정**에서는 표시 이름, 자기소개, 비밀번호를 변경할 수 있습니다.

