'use strict';

(async () => {
  const parameters = new URLSearchParams(location.search);
  const mode = parameters.get('mode');
  const id = parameters.get('id');
  const sheet = document.querySelector('.sheet');
  const toolbar = document.querySelector('.toolbar');
  const back = document.createElement('button');
  back.type = 'button';
  back.className = 'secondary';
  back.textContent = '我的角色';
  toolbar.prepend(back);
  if (!id && mode !== 'new' && mode !== 'import') {
    back.onclick = () => location.assign('characters.html');
    return;
  }

  let saved = Boolean(id);
  const storageId = id || ensureSheetId();
  let timer;
  let dirty = false;
  let pending = 0;
  let queue = Promise.resolve();

  function save() {
    clearTimeout(timer);
    if (!dirty) return queue;
    __sheetId = storageId;
    const data = collectData();
    dirty = false;
    pending++;
    queue = queue.catch(() => {}).then(async () => {
      if (saved) await CharacterDB.update(data);
      else {
        await CharacterDB.create(data);
        saved = true;
        history.replaceState(null, '', 'character.html?id=' + encodeURIComponent(storageId));
      }
    }).catch(error => {
      dirty = true;
      throw error;
    }).finally(() => pending--);
    return queue;
  }

  function reportError(error) {
    console.error(error);
    toast('本地存档失败，请重试或导出 JSON 备份');
  }

  if (id) {
    sheet.inert = toolbar.inert = true;
    try {
      const data = await CharacterDB.get(id);
      if (!data) throw new Error('找不到该本地角色');
      characterApplyData(data);
    } catch (error) {
      toolbar.inert = false;
      back.onclick = () => location.assign('characters.html');
      toast(error.message || '无法读取本地角色');
      return;
    }
    sheet.inert = toolbar.inert = false;
  }

  const schedule = () => {
    dirty = true;
    clearTimeout(timer);
    timer = setTimeout(() => save().catch(reportError), 350);
  };
  document.addEventListener('input', schedule);
  document.addEventListener('change', event => {
    if (event.target.type !== 'file') schedule();
  });
  document.addEventListener('character-imported', () => {
    __sheetId = storageId;
    schedule();
  });
  sheet.addEventListener('click', event => {
    if (event.target.closest('.prof, #add-summon, .summon-delete, details > summary')) schedule();
  });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) save().catch(reportError);
  });
  window.addEventListener('beforeunload', event => {
    if (!dirty && !pending) return;
    save().catch(reportError);
    event.preventDefault();
    event.returnValue = '';
  });
  back.onclick = async () => {
    try {
      await save();
      location.assign('characters.html');
    } catch (error) { reportError(error); }
  };
  if (mode === 'import') toast('点击「读取 JSON」选择角色卡文件');
})();
