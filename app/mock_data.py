"""Preview-only sample content. The backend team can replace this with MySQL queries."""

CURRENT_USER = {
    "user_id": "jineon",
    "display_name": "Jineon Kim",
    "avatar_url": "/static/images/demo/avatar-jineon.svg",
    "bio": "일상의 장면을 기록합니다. 📸",
}

USERS = {
    "jineon": {**CURRENT_USER, "location": "Seoul, Korea", "followers_count": 128, "following_count": 91,
               "post_count": 2, "is_following": False},
    "alice": {"user_id": "alice", "display_name": "Alice Park", "avatar_url": "/static/images/demo/avatar-alice.svg",
              "bio": "빛과 바다를 좋아해요. 🌊", "location": "Busan, Korea", "followers_count": 854,
              "following_count": 216, "post_count": 2, "is_following": True},
    "noah": {"user_id": "noah", "display_name": "Noah Lee", "avatar_url": "/static/images/demo/avatar-noah.svg",
             "bio": "도시의 작은 순간들", "location": "Seoul, Korea", "followers_count": 532,
             "following_count": 184, "post_count": 1, "is_following": True},
    "mina": {"user_id": "mina", "display_name": "Mina Choi", "avatar_url": "/static/images/demo/avatar-mina.svg",
             "bio": "자연과 디자인 사이", "location": "Jeju, Korea", "followers_count": 312,
             "following_count": 205, "post_count": 1, "is_following": False},
}

POSTS = [
    {"post_id": 105, "author_id": "alice", "author_name": "Alice Park", "author_avatar": USERS["alice"]["avatar_url"],
     "image_url": "/static/images/demo/coast.svg", "image_alt": "푸른 바다와 해안 절벽 일러스트",
     "caption": "좋은 장면은 오래 남는다. 오늘도 바다와 함께 🌊 #travel #sea", "created_at": "12분 전", "location": "Busan, Korea",
     "like_count": 248, "comment_count": 2, "is_liked": False,
     "comments": [{"author_id": "jineon", "text": "색감 너무 좋아요!"}, {"author_id": "mina", "text": "@alice 멋진 풍경이네요"}]},
    {"post_id": 104, "author_id": "noah", "author_name": "Noah Lee", "author_avatar": USERS["noah"]["avatar_url"],
     "image_url": "/static/images/demo/city.svg", "image_alt": "노을빛 도시 스카이라인 일러스트",
     "caption": "퇴근길 도시의 불빛들. #city #sunset", "created_at": "2시간 전", "location": "Seoul, Korea",
     "like_count": 136, "comment_count": 1, "is_liked": True,
     "comments": [{"author_id": "alice", "text": "영화의 한 장면 같아!"}]},
    {"post_id": 103, "author_id": "jineon", "author_name": "Jineon Kim", "author_avatar": USERS["jineon"]["avatar_url"],
     "image_url": "/static/images/demo/flower.svg", "image_alt": "밝은 배경의 꽃 일러스트",
     "caption": "조금 느리게 걸으면서 발견한 것들. 🌼", "created_at": "어제", "location": "Seoul, Korea",
     "like_count": 82, "comment_count": 1, "is_liked": False,
     "comments": [{"author_id": "noah", "text": "분위기 좋다!"}]},
    {"post_id": 102, "author_id": "mina", "author_name": "Mina Choi", "author_avatar": USERS["mina"]["avatar_url"],
     "image_url": "/static/images/demo/architecture.svg", "image_alt": "따뜻한 색조의 건축물 일러스트",
     "caption": "건물 사이로 떨어진 햇살. #architecture", "created_at": "2일 전", "location": "Jeju, Korea",
     "like_count": 191, "comment_count": 0, "is_liked": False, "comments": []},
    {"post_id": 101, "author_id": "jineon", "author_name": "Jineon Kim", "author_avatar": USERS["jineon"]["avatar_url"],
     "image_url": "/static/images/demo/forest.svg", "image_alt": "숲과 산의 풍경 일러스트",
     "caption": "주말의 산책 기록. #nature", "created_at": "3일 전", "location": "Incheon, Korea",
     "like_count": 64, "comment_count": 0, "is_liked": False, "comments": []},
    {"post_id": 100, "author_id": "alice", "author_name": "Alice Park", "author_avatar": USERS["alice"]["avatar_url"],
     "image_url": "/static/images/demo/architecture.svg", "image_alt": "아치형 건축물 일러스트",
     "caption": "오래된 공간이 가진 따뜻함.", "created_at": "지난주", "location": "Gyeongju, Korea",
     "like_count": 99, "comment_count": 0, "is_liked": False, "comments": []},
]
