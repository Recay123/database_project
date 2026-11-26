/* FRAME v4 enhancements. Executes after app.js; preserves its existing preview behavior. */
(() => {
  'use strict';
  const backend = document.body?.dataset.integrationMode === 'backend';
  const uid = document.querySelector('meta[name="current-user-id"]')?.content || '';
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
  const toast = message => {
    const el = document.getElementById('app-toast');
    if (!el) { window.alert(message); return; }
    el.textContent = message;
    el.classList.add('is-visible');
    clearTimeout(el._frameV4timer);
    el._frameV4timer = setTimeout(() => el.classList.remove('is-visible'), 4000);
  };
  const request = async (url, method, payload) => {
    const headers = { Accept: 'application/json', 'X-CSRF-Token': csrf };
    const response = await fetch(url, { method, body: payload,
      headers, credentials: 'same-origin', redirect: 'follow' });
    if (!response.ok) {
      let message = `요청을 처리할 수 없습니다. (${response.status})`;
      try { const json = await response.json(); if (json.detail) message = String(json.detail); } catch (_) {}
      throw new Error(message);
    }
    return response.json();
  };
  const activeBackend = () => {
    if (backend) return true;
    toast('현재는 UI 미리보기입니다. 수정·삭제·프로필 사진 저장은 백엔드 서버에서 확인해 주세요.');
    return false;
  };

  // 회원가입 성공 안내는 서버 렌더링 플래시 메시지로 표시된다.

  // 기존 피드나 게시물 팝업에서 소유자에게만 수정·삭제를 노출한다.
  let postMap = new Map();
  try {
    const raw = document.getElementById('page-posts-json')?.textContent;
    postMap = new Map((JSON.parse(raw || '[]')).map(post => [String(post.post_id), post]));
  } catch (_) { /* 페이지에 게시물이 없는 경우 */ }

  document.querySelectorAll('[data-post-open]').forEach(button => {
    button.addEventListener('click', () => {
      const postId = String(button.dataset.postOpen);
      const post = postMap.get(postId);
      const tools = document.getElementById('v4-dialog-post-tools');
      if (!tools) return;
      tools.hidden = !post || post.author_id !== uid;
      tools.dataset.postId = postId;
    });
  });

  const editor = document.getElementById('v4-post-editor');
  const editorInput = editor?.querySelector('[name="caption"]');
  const editorForm = editor?.querySelector('form');
  document.addEventListener('click', event => {
    const editPost = event.target.closest('[data-v4-edit-post]');
    if (editPost) {
      const postId = editPost.dataset.postId || editPost.closest('[data-post-id]')?.dataset.postId;
      const post = postMap.get(String(postId));
      if (!post || post.author_id !== uid || !editor || !editorInput) return;
      editorForm.dataset.postId = String(postId);
      editorInput.value = post.caption || '';
      editor.showModal();
    }
    const deletePost = event.target.closest('[data-v4-delete-post]');
    if (deletePost) {
      const postId = deletePost.dataset.postId || deletePost.closest('[data-post-id]')?.dataset.postId;
      const post = postMap.get(String(postId));
      if (!post || post.author_id !== uid || !activeBackend()) return;
      if (!confirm('게시물을 삭제할까요? 사진과 댓글, 좋아요도 함께 삭제됩니다.')) return;
      deletePost.disabled = true;
      request(`/posts/${encodeURIComponent(postId)}`, 'DELETE').then(() => location.reload())
        .catch(e => toast(e.message)).finally(() => { deletePost.disabled = false; });
    }
  });
  editorForm?.addEventListener('submit', async e => {
    e.preventDefault();
    if (!activeBackend()) return;
    const postId = editorForm.dataset.postId;
    if (!postId || !postMap.has(postId)) return;
    const submit = editorForm.querySelector('[type="submit"]');
    submit.disabled = true;
    try {
      await request(`/posts/${encodeURIComponent(postId)}`, 'PATCH', new FormData(editorForm));
      editor.close();
      location.reload(); // 원본 app.js의 내부 postMap 및 팝업도 DB 기준으로 갱신
    } catch (error) { toast(error.message); }
    finally { submit.disabled = false; }
  });
  editor?.querySelector('[data-v4-close-editor]')?.addEventListener('click', () => editor.close());

  // 댓글: 기존 삭제 기능은 유지. 자기 댓글에만 수정 버튼을 추가한다.
  const enhanceCommentRows = root => {
    (root.matches?.('.comment-line') ? [root] : root.querySelectorAll?.('.comment-line') || []).forEach(row => {
      if (row.dataset.v4Enhanced === 'true') return;
      row.dataset.v4Enhanced = 'true';
      const owner = row.querySelector('strong a')?.textContent?.trim();
      const postId = row.dataset.postId;
      const commentId = row.dataset.commentId;
      if (owner !== uid || !postId || !commentId) return;
      const editButton = document.createElement('button');
      editButton.type = 'button';
      editButton.className = 'v4-comment-action';
      editButton.textContent = '수정';
      editButton.dataset.v4EditComment = '';
      row.append(document.createTextNode(' '), editButton);
      const deleteButton = row.querySelector('[data-delete-comment]');
      if (deleteButton) deleteButton.classList.add('v4-comment-action', 'danger');
    });
  };
  enhanceCommentRows(document);
  const observeComments = new MutationObserver(mutations => {
    mutations.forEach(m => m.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE && node.closest?.('.comments-list, .dialog-comments')) enhanceCommentRows(node);
    }));
  });
  document.querySelectorAll('.comments-list, .dialog-comments').forEach(el =>
    observeComments.observe(el, { childList: true, subtree: true }));

  document.addEventListener('click', event => {
    const button = event.target.closest('[data-v4-edit-comment]');
    if (!button || !activeBackend()) return;
    const row = button.closest('.comment-line');
    if (!row || row.querySelector('.v4-comment-edit-form')) return;
    const text = row.querySelector('[data-mention-text]') || row.querySelector('span');
    if (!text) return;
    const originalText = text.textContent;
    const form = document.createElement('form');
    form.className = 'v4-comment-edit-form';
    const area = document.createElement('textarea');
    area.name = 'text'; area.maxLength = 1000; area.required = true; area.rows = 3;
    area.value = originalText;
    const save = document.createElement('button');
    save.type = 'submit'; save.className = 'btn btn-primary btn-small'; save.textContent = '저장';
    const cancel = document.createElement('button');
    cancel.type = 'button'; cancel.className = 'btn btn-outline btn-small'; cancel.textContent = '취소';
    form.append(area, save, cancel);
    cancel.addEventListener('click', () => { form.remove(); row.hidden = false; });
    row.insertAdjacentElement('afterend', form);
    row.hidden = true;
    area.focus();
    form.addEventListener('submit', async e => {
      e.preventDefault();
      save.disabled = true;
      const postId = row.dataset.postId;
      const commentId = row.dataset.commentId;
      try {
        await request(`/posts/${encodeURIComponent(postId)}/comments/${encodeURIComponent(commentId)}`,
          'PATCH', new FormData(form));
        // 피드 / 팝업 중복 댓글을 한 번에 동기화하려면 새로고침이 가장 안전하다.
        location.reload();
      } catch (error) { toast(error.message); }
      finally { save.disabled = false; }
    });
  });

  // 아바타 업로드: 내 프로필에만 파일 선택 버튼이 존재한다.
  const avatarFile = document.getElementById('v4-avatar-file');
  const avatarButton = document.getElementById('v4-avatar-pick');
  avatarButton?.addEventListener('click', () => { if (activeBackend()) avatarFile?.click(); });
  avatarFile?.addEventListener('change', async () => {
    const file = avatarFile.files?.[0];
    if (!file) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)
      || file.size === 0 || file.size > 8 * 1024 * 1024) {
      toast('JPG, PNG, WEBP 사진만 사용할 수 있고 크기는 8MB 이하여야 합니다.');
      avatarFile.value = '';
      return;
    }
    const data = new FormData();
    data.append('avatar', file);
    avatarButton.disabled = true;
    avatarButton.textContent = '업로드 중...';
    try {
      await request('/users/me/avatar', 'POST', data);
      location.reload();
    } catch (error) {
      toast(error.message);
      avatarButton.disabled = false;
      avatarButton.textContent = '프로필 사진 변경';
      avatarFile.value = '';
    }
  });
})();
