/* FRAME frontend: preview mode uses local demo state; backend mode sends mutations to FastAPI. */
(() => {
  const toastEl = document.getElementById('app-toast');
  let toastTimer;
  const toast = message => {
    if (!toastEl) return;
    toastEl.textContent = message;
    toastEl.classList.add('is-visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove('is-visible'), 3200);
  };
  const safeGet = key => { try { return localStorage.getItem(key); } catch { return null; } };
  const safeSet = (key, value) => { try { localStorage.setItem(key, value); } catch {} };
  const backendMode = document.body?.dataset.integrationMode === 'backend';
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';
  const sendMutation = async (url, method, data = null) => {
    const headers = { 'Accept': 'application/json' };
    if (csrfToken) headers['X-CSRF-Token'] = csrfToken;
    const response = await fetch(url, {
      method, body: data, headers, credentials: 'same-origin', redirect: 'follow'
    });
    if (!response.ok) {
      let detail = `서버 오류 (${response.status})`;
      try { const json = await response.json(); if (typeof json.detail === 'string') detail = json.detail; } catch {}
      throw new Error(detail);
    }
    return await response.json();
  };
  const reportRequestError = error => toast(error?.message || '서버 연결에 실패했어요.');


  const currentUserId = document.querySelector('meta[name="current-user-id"]')?.content || '';

  // 사용자 입력은 HTML로 해석하지 않고 텍스트와 링크 노드로만 만든다.
  const renderMentions = (target, text) => {
    target.replaceChildren();
    const value = String(text || '');
    const pattern = /(^|[^A-Za-z0-9_@])@([A-Za-z0-9_]{3,30})(?![A-Za-z0-9_])/g;
    let offset = 0;
    for (const match of value.matchAll(pattern)) {
      target.append(document.createTextNode(value.slice(offset, match.index) + match[1]));
      const link = document.createElement('a');
      link.href = `/profile/${encodeURIComponent(match[2])}`;
      link.textContent = `@${match[2]}`;
      target.append(link);
      offset = match.index + match[0].length;
    }
    target.append(document.createTextNode(value.slice(offset)));
  };
  document.querySelectorAll('[data-mention-text]').forEach(el => renderMentions(el, el.textContent));

  const commentRow = (comment, postId) => {
    const row = document.createElement('p');
    row.className = 'comment-line';
    row.dataset.postId = String(postId);
    row.dataset.commentId = String(comment.comment_id ?? '');
    const strong = document.createElement('strong');
    const author = document.createElement('a');
    author.textContent = comment.author_id;
    author.href = `/profile/${encodeURIComponent(comment.author_id)}`;
    strong.append(author);
    const text = document.createElement('span');
    renderMentions(text, comment.text);
    row.append(strong, document.createTextNode(' '), text);
    if (backendMode && comment.author_id === currentUserId && comment.comment_id != null) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.deleteComment = '';
      button.dataset.postId = String(postId);
      button.dataset.commentId = String(comment.comment_id);
      button.textContent = '삭제';
      button.setAttribute('aria-label', '내 댓글 삭제');
      row.append(document.createTextNode(' '), button);
    }
    return row;
  };

  // 1. Accent/theme selection (browser-local; no account DB yet).
  const themes = ['forest', 'ocean', 'lavender', 'coral'];
  const selectedTheme = themes.includes(safeGet('frame-theme')) ? safeGet('frame-theme') : 'forest';
  const renderTheme = theme => {
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('input[name="theme"]').forEach(input => {
      input.checked = input.value === theme;
    });
  };
  renderTheme(selectedTheme);
  document.querySelectorAll('input[name="theme"]').forEach(input => {
    input.addEventListener('change', () => {
      if (!input.checked || !themes.includes(input.value)) return;
      safeSet('frame-theme', input.value);
      renderTheme(input.value);
      toast('화면 테마를 변경했어요. 다른 페이지에도 유지됩니다.');
    });
  });

  // 2. Accessible native dialogs, integrated with browser Back.
  let activeDialog = null;
  let lastFocus = null;
  const closeDirect = () => {
    if (!activeDialog) return;
    if (activeDialog.open) activeDialog.close();
    activeDialog = null;
    lastFocus?.focus?.({ preventScroll: true });
    lastFocus = null;
  };
  const openDialog = (id, hash) => {
    const dialog = document.getElementById(id);
    if (!dialog) return;
    if (activeDialog) closeDirect();
    lastFocus = document.activeElement;
    dialog.showModal();
    activeDialog = dialog;
    // Back restores previous URL and closes the modal without navigating away.
    history.pushState({ frameModal: true }, '', `#${hash}`);
  };
  const closeModal = () => {
    if (history.state?.frameModal) history.back();
    else closeDirect();
  };
  window.addEventListener('popstate', closeDirect);
  document.querySelectorAll('.frame-dialog').forEach(dialog => {
    dialog.addEventListener('cancel', e => { e.preventDefault(); closeModal(); });
    dialog.addEventListener('click', e => { if (e.target === dialog) closeModal(); });
    dialog.querySelectorAll('[data-close-modal]').forEach(button => button.addEventListener('click', closeModal));
  });

  // 3. Profile picture viewer. Avatar and name are independent controls.
  document.querySelectorAll('[data-avatar-open]').forEach(button => {
    button.addEventListener('click', () => {
      const img = document.getElementById('avatar-dialog-image');
      const title = document.getElementById('avatar-dialog-name');
      if (!img || !title) return;
      img.src = button.dataset.avatarSrc;
      img.alt = `${button.dataset.avatarName}님의 프로필 사진`;
      title.textContent = button.dataset.avatarName;
      openDialog('avatar-dialog', 'avatar');
    });
  });

  // 4. Post-detail viewer. Data stays in a JSON script rather than HTML attributes.
  const postsJson = document.getElementById('page-posts-json');
  let postMap = new Map();
  if (postsJson) {
    try {
      const posts = JSON.parse(postsJson.textContent);
      postMap = new Map(posts.map(post => [String(post.post_id), post]));
    } catch { /* preview can still display the feed */ }
  }
  document.querySelectorAll('[data-post-open]').forEach(button => {
    button.addEventListener('click', () => {
      const post = postMap.get(String(button.dataset.postOpen));
      if (!post) return;
      document.getElementById('dialog-post-image').src = post.image_url;
      document.getElementById('dialog-post-image').alt = post.image_alt || '게시물 사진';
      const author = document.getElementById('dialog-post-author');
      author.textContent = `@${post.author_id}`;
      author.href = `/profile/${encodeURIComponent(post.author_id)}`;
      document.getElementById('dialog-post-location').textContent = post.location || '';
      renderMentions(document.getElementById('dialog-post-caption'), post.caption);
      document.getElementById('dialog-post-likes').textContent = `좋아요 ${post.like_count || 0}개`;
      document.getElementById('dialog-post-date').textContent = post.created_at || '';
      const comments = document.getElementById('dialog-post-comments');
      comments.dataset.commentsList = String(post.post_id);
      comments.replaceChildren();
      for (const comment of post.comments || []) {
        comments.append(commentRow(comment, post.post_id));
      }
      if (!comments.children.length) comments.textContent = '아직 댓글이 없어요.';
      openDialog('post-dialog', `post-${encodeURIComponent(post.post_id)}`);
    });
  });

  // 서버에서 삭제에 성공한 뒤 피드와 상세창을 함께 갱신한다.
  document.addEventListener('click', async event => {
    const button = event.target.closest('[data-delete-comment]');
    if (!button || !backendMode || button.disabled) return;
    if (!window.confirm('이 댓글을 삭제할까요?')) return;
    const { postId, commentId } = button.dataset;
    button.disabled = true;
    try {
      const result = await sendMutation(`/posts/${encodeURIComponent(postId)}/comments/${encodeURIComponent(commentId)}`, 'DELETE');
      const post = postMap.get(String(postId));
      if (post) {
        post.comments = (post.comments || []).filter(c => String(c.comment_id) !== commentId);
        post.comment_count = Number(result.comment_count);
      }
      document.querySelectorAll('[data-comment-id]').forEach(row => {
        if (row.classList.contains('comment-line') && row.dataset.postId === postId && row.dataset.commentId === commentId) row.remove();
      });
      const detail = document.getElementById('dialog-post-comments');
      if (detail?.dataset.commentsList === postId && !detail.children.length) detail.textContent = '아직 댓글이 없어요.';
      toast('댓글을 삭제했어요.');
    } catch (error) { reportRequestError(error); }
    finally { button.disabled = false; }
  });

  // 5. Stories: click to view, then ring becomes grey. Read status is per browser.
  const storyButtons = [...document.querySelectorAll('[data-story-open]')];
  // Use an in-memory Set as well, so read rings work even when storage is blocked.
  const viewedStories = new Set(storyButtons.filter(button => safeGet(`frame-story-seen-${button.dataset.storyUser}`) === 'true').map(button => button.dataset.storyUser));
  let currentStoryIndex = 0;
  const renderStoryStatus = () => {
    storyButtons.forEach(button => {
      const seen = viewedStories.has(button.dataset.storyUser);
      button.classList.toggle('is-viewed', seen);
      button.setAttribute('aria-label', `${button.dataset.storyUser}님의 스토리 ${seen ? '다시' : ''}보기`);
    });
  };
  const displayStory = index => {
    if (!storyButtons.length) return;
    currentStoryIndex = (index + storyButtons.length) % storyButtons.length;
    const button = storyButtons[currentStoryIndex];
    document.getElementById('story-avatar').src = button.dataset.storyAvatar;
    document.getElementById('story-username').textContent = `@${button.dataset.storyUser}`;
    document.getElementById('story-photo').src = button.dataset.storyImage;
    document.getElementById('story-photo').alt = `${button.dataset.storyName}의 스토리 사진`;
    document.getElementById('story-caption').textContent = button.dataset.storyCaption || '';
    document.getElementById('story-progress-fill').style.width = `${((currentStoryIndex + 1) / storyButtons.length) * 100}%`;
    viewedStories.add(button.dataset.storyUser);
    safeSet(`frame-story-seen-${button.dataset.storyUser}`, 'true');
    renderStoryStatus();
  };
  storyButtons.forEach((button, index) => button.addEventListener('click', () => {
    displayStory(index);
    openDialog('story-dialog', `story-${encodeURIComponent(button.dataset.storyUser)}`);
  }));
  document.getElementById('story-prev')?.addEventListener('click', () => displayStory(currentStoryIndex - 1));
  document.getElementById('story-next')?.addEventListener('click', () => displayStory(currentStoryIndex + 1));
  document.addEventListener('keydown', e => {
    if (document.getElementById('story-dialog')?.open) {
      if (e.key === 'ArrowLeft') { e.preventDefault(); displayStory(currentStoryIndex - 1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); displayStory(currentStoryIndex + 1); }
    }
  });
  renderStoryStatus();

  // 6. Like/comment/follow call backend endpoints in integration mode; preview stays local.
  document.querySelectorAll('[data-like-button]').forEach(button => {
    const postId = button.dataset.postId;
    const initial = button.dataset.initialLiked === 'true';
    const initialCount = Number(button.dataset.initialCount);
    const stored = backendMode ? null : safeGet(`frame-liked-${postId}`);
    let liked = stored === null ? initial : stored === 'true';
    let likeCount = initialCount + Number(liked) - Number(initial);
    const countEl = document.querySelector(`[data-like-count="${CSS.escape(postId)}"]`);
    const render = () => {
      button.classList.toggle('is-liked', liked);
      button.setAttribute('aria-pressed', String(liked));
      if (countEl) countEl.textContent = String(likeCount);
    };
    button.addEventListener('click', async () => {
      if (!backendMode) {
        liked = !liked;
        likeCount = initialCount + Number(liked) - Number(initial);
        safeSet(`frame-liked-${postId}`, String(liked));
      } else {
        button.disabled = true;
        try {
          const result = await sendMutation(`/posts/${encodeURIComponent(postId)}/likes`, liked ? 'DELETE' : 'POST');
          liked = Boolean(result.liked);
          likeCount = Number(result.like_count);
          const post = postMap.get(String(postId));
          if (post) { post.is_liked = liked; post.like_count = likeCount; }
        } catch (error) { reportRequestError(error); }
        finally { button.disabled = false; }
      }
      render();
    });
    render();
  });
  document.querySelectorAll('[data-comment-form]').forEach(form => {
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const input = form.querySelector('[name="text"]');
      const postId = form.dataset.commentForm;
      const list = document.querySelector(`[data-comments-list="${CSS.escape(postId)}"]`);
      const value = input?.value.trim();
      if (!value || !list) return;
      let comment = { author_id: 'jineon', text: value };
      if (backendMode) {
        const submit = form.querySelector('[type="submit"]');
        if (submit) submit.disabled = true;
        try {
          const result = await sendMutation(`/posts/${encodeURIComponent(postId)}/comments`, 'POST', new FormData(form));
          comment = result.comment;
          if (!comment || typeof comment.author_id !== 'string' || typeof comment.text !== 'string') throw new Error('댓글 응답 형식이 올바르지 않습니다.');
        } catch (error) { reportRequestError(error); return; }
        finally { if (submit) submit.disabled = false; }
      }
      document.querySelectorAll(`[data-comments-list="${CSS.escape(postId)}"]`).forEach(target => {
        if (target.id === 'dialog-post-comments' && !target.children.length) target.replaceChildren();
        target.append(commentRow(comment, postId));
      });
      input.value = '';
      const post = postMap.get(String(postId));
      if (post) {
        post.comments = [...(post.comments || []), comment];
        post.comment_count = post.comments.length;
      }
      if (!backendMode) toast('댓글이 화면에 추가됐어요. (서버 저장 전)');
    });
  });
  document.querySelectorAll('[data-focus-comment]').forEach(button => {
    button.addEventListener('click', () => document.getElementById(`comment-input-${button.dataset.focusComment}`)?.focus());
  });
  document.querySelectorAll('[data-bookmark-button]').forEach(button => {
    button.addEventListener('click', () => {
      const saved = !button.classList.contains('is-saved');
      button.classList.toggle('is-saved', saved);
      button.setAttribute('aria-pressed', String(saved));
      toast(saved ? '데모: 저장됨' : '데모: 저장 해제됨');
    });
  });
  document.querySelectorAll('[data-demo-action="share"]').forEach(button => button.addEventListener('click', () => toast('공유 기능은 추가 연동 대상입니다.')));
  document.querySelectorAll('[data-follow-button]').forEach(button => {
    const user = button.dataset.user;
    const initial = button.dataset.initialFollowing === 'true';
    const stored = backendMode ? null : safeGet(`frame-follow-${user}`);
    let following = stored === null ? initial : stored === 'true';
    const followerCount = document.querySelector('[data-follower-count]');
    const baseline = followerCount ? Number(followerCount.textContent) : null;
    let serverFollowers = baseline;
    const render = () => {
      button.textContent = following ? '팔로잉 ✓' : '팔로우 +';
      button.classList.toggle('btn-primary', !following);
      button.classList.toggle('btn-outline', following);
      if (followerCount && serverFollowers !== null) followerCount.textContent = String(serverFollowers);
    };
    button.addEventListener('click', async () => {
      if (!backendMode) {
        following = !following;
        safeSet(`frame-follow-${user}`, String(following));
        serverFollowers = baseline === null ? null : baseline + Number(following) - Number(initial);
        toast(following ? `@${user} 팔로우 (데모)` : `@${user} 팔로우 취소 (데모)`);
      } else {
        button.disabled = true;
        try {
          const result = await sendMutation(`/users/${encodeURIComponent(user)}/follow`, following ? 'DELETE' : 'POST');
          following = Boolean(result.is_following);
          serverFollowers = Number(result.followers_count);
        } catch (error) { reportRequestError(error); }
        finally { button.disabled = false; }
      }
      render();
    });
    render();
  });

  // File preview + validation. A valid form really POSTs to preview server.
  const uploadInput = document.getElementById('image-file');
  const uploadPreview = document.getElementById('upload-image');
  const uploadEmpty = document.getElementById('upload-empty');
  const fileLabel = document.getElementById('selected-file');
  const previewZone = document.querySelector('[data-click-upload]');
  let objectUrl = null;
  const validImage = file => file && ['image/jpeg', 'image/png', 'image/webp'].includes(file.type) && file.size > 0 && file.size <= 8 * 1024 * 1024;
  if (previewZone && uploadInput) {
    previewZone.addEventListener('click', () => uploadInput.click());
    previewZone.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); uploadInput.click(); }
    });
    uploadInput.addEventListener('change', () => {
      const file = uploadInput.files?.[0];
      if (!file) return;
      if (!validImage(file)) {
        toast('JPG·PNG·WEBP 이미지만 선택할 수 있으며 최대 8MB입니다.');
        uploadInput.value = '';
        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = null; uploadPreview.hidden = true; uploadEmpty.hidden = false;
        fileLabel.textContent = '아직 선택한 파일이 없습니다.';
        return;
      }
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = URL.createObjectURL(file);
      uploadPreview.src = objectUrl;
      uploadPreview.hidden = false;
      uploadEmpty.hidden = true;
      fileLabel.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
    });
  }
  const caption = document.getElementById('caption');
  caption?.addEventListener('input', () => {
    document.getElementById('caption-count').textContent = String(caption.value.length);
  });
  document.querySelector('[data-demo-form="upload"]')?.addEventListener('submit', e => {
    if (!validImage(uploadInput?.files?.[0])) {
      e.preventDefault();
      toast('먼저 8MB 이하 이미지 파일을 선택해주세요.');
    }
    // When valid, let the browser POST multipart/form-data to /posts.
  });
  if (new URLSearchParams(location.search).get('uploaded') === '1') {
    toast(backendMode ? '게시물을 공유했어요!' : '게시물이 로컬 미리보기에 저장됐어요!');
  }

  if (backendMode && document.querySelector('[data-password-changed]')) {
    const url = new URL(window.location.href);
    url.searchParams.delete('changed');
    history.replaceState(history.state, '', url.pathname + url.search + url.hash);
  }

  // Preview simulates auth forms. Backend uses native form submissions.
  document.querySelectorAll('[data-demo-form]:not([data-demo-form="upload"])').forEach(form => {
    form.addEventListener('submit', e => {
      const kind = form.dataset.demoForm;
      const data = new FormData(form);
      // In backend mode, preserve native HTML form POST if client-side validation passes.
      // Preview mode keeps the existing demo-only navigation and messages.
      if (!backendMode) e.preventDefault();
      if (kind === 'login') {
        if (backendMode) return;
        toast('데모 화면으로 이동합니다. (실제 로그인 아님)');
        window.location.href = '/feed';
      } else if (kind === 'signup') {
        const error = document.getElementById('signup-error');
        if (data.get('password') !== data.get('confirm_password')) {
          e.preventDefault(); error.hidden = false; error.textContent = '비밀번호와 비밀번호 확인이 일치하지 않습니다.'; return;
        }
        error.hidden = true;
        if (backendMode) return;
        toast('회원가입 화면 동작 확인 완료. 실제 계정은 저장되지 않습니다.');
        window.location.href = '/feed';
      } else if (kind === 'password') {
        const error = document.getElementById('password-error');
        if (data.get('new_password') !== data.get('confirm_password')) {
          e.preventDefault(); error.hidden = false; error.textContent = '새 비밀번호와 확인이 일치하지 않습니다.'; return;
        }
        error.hidden = true;
        if (backendMode) return;
        toast('데모: 비밀번호 변경 양식이 확인됐어요. DB에는 반영되지 않습니다.');
        form.reset();
      }
    });
  });
})();
