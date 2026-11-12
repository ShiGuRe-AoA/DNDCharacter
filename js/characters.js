'use strict';

const list = document.querySelector('#characters');
const search = document.querySelector('#search');
const status = document.querySelector('#status');
const date = new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' });
const isCloud = new URLSearchParams(location.search).get('storage') === 'cloud';
const storageQuery = isCloud ? '&storage=cloud' : '';
const account = document.querySelector('#cloud-account');
const characterActions = document.querySelector('#character-actions');
const activeTab = document.querySelector(isCloud ? '#cloud-tab' : '#local-tab');
activeTab.classList.add('primary');
activeTab.setAttribute('aria-current', 'page');
let repository = CharacterDB;
let characters = [];

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function button(label, action) {
  const node = element('button', label, 'button');
  node.type = 'button';
  node.onclick = async () => {
    node.disabled = true;
    try { await action(); }
    catch (error) { status.textContent = error.message || '操作失败，请重试。'; console.error(error); }
    finally { node.disabled = false; }
  };
  return node;
}

function exportJSON(data, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = element('a');
  link.href = url;
  link.download = name.replace(/[<>:"/\\|?*]/g, '-') + '.json';
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function card(data) {
  const { name = '', race = '', classText = '' } = data.identity || {};
  const title = String(name ?? '').trim() || '未命名角色';
  const node = element('article', '', 'panel');
  if (typeof data.portrait === 'string' && /^data:image\/(png|jpeg|webp|gif);base64,/i.test(data.portrait)) {
    const portrait = element('img', '', 'portrait');
    portrait.src = data.portrait;
    portrait.alt = title + '的立绘';
    portrait.loading = 'lazy';
    node.append(portrait);
  }

  node.append(element('h2', title));
  node.append(element('p', [race, classText].filter(Boolean).join(' · ') || '种族和职业待填写'));
  const time = Date.parse(data.exportedAt);
  node.append(element('p', Number.isFinite(time) ? (isCloud ? '云端存档 · ' : '本机存档 · ') + date.format(time) : (isCloud ? '云端存档' : '本机存档'), 'details'));
  const actions = element('div', '', 'actions');
  const edit = element('a', '打开编辑', 'button primary');
  edit.href = 'character.html?id=' + encodeURIComponent(data.sheetId) + storageQuery;
  actions.append(edit, button('复制', async () => {
    const copy = structuredClone(data);
    copy.sheetId = crypto.randomUUID();
    copy.identity = { ...copy.identity, name: title + '（副本）' };
    delete copy.formattedText?.['identity.name'];
    copy.exportedAt = new Date().toISOString();
    await repository.create(copy);
    await refresh();
  }), button('重命名', async () => {
    const nextName = window.prompt('输入新的角色名称', name)?.trim();
    if (!nextName) return;
    const latest = await repository.get(data.sheetId);
    if (!latest) return refresh();
    latest.identity = { ...latest.identity, name: nextName };
    delete latest.formattedText?.['identity.name'];
    latest.exportedAt = new Date().toISOString();
    await repository.update(latest);
    await refresh();
  }), button('导出 JSON', () => exportJSON(data, title)), button('删除', async () => {
    if (!window.confirm('删除「' + title + '」的' + (isCloud ? '云端' : '本机') + '存档？')) return;
    await repository.delete(data.sheetId);
    await refresh();
  }));
  if (!isCloud) actions.append(button('复制到云端', async () => {
    const user = await Cloud.user();
    if (!user) {
      location.assign('account.html');
      return;
    }
    const source = await CharacterDB.get(data.sheetId);
    if (!source) throw new Error('找不到该本机角色');
    if (!window.confirm('把「' + title + '」复制到账号「' + user.username + '」？')) return;
    await Cloud.cards(user).create({ ...source, sheetId: crypto.randomUUID() });
    status.textContent = '已复制到「' + user.username + '」的云端角色。';
  }));
  node.append(actions);
  return node;
}

function render() {
  const query = search.value.trim().toLocaleLowerCase();
  const filtered = characters.filter(({ identity = {} }) =>
    [identity.name, identity.race, identity.classText].some(value => String(value ?? '').toLocaleLowerCase().includes(query)));
  list.replaceChildren(...filtered.map(card));
  status.textContent = filtered.length ? filtered.length + ' 张角色卡'
    : query ? '没有符合搜索条件的角色。' : '当前没有角色。创建一张角色卡，或导入已有的 JSON。';
}

async function refresh() {
  characters = (await repository.getAll()).sort((a, b) => Date.parse(b.exportedAt) - Date.parse(a.exportedAt));
  render();
}

async function initialize() {
  if (isCloud) {
    characterActions.hidden = true;
    status.textContent = '正在读取云端角色…';
    const user = await Cloud.user();
    if (!user) {
      status.replaceChildren('登录后可以查看云端角色。 ', Object.assign(document.createElement('a'), {
        href: 'account.html', textContent: '登录 / 注册'
      }));
      return;
    }
    repository = Cloud.cards(user);
    account.textContent = '当前账号：' + user.username;
    for (const link of characterActions.querySelectorAll('a')) link.href += storageQuery;
  }
  await refresh();
  characterActions.hidden = false;
  search.addEventListener('input', render);
}

window.addEventListener('pageshow', event => {
  if (event.persisted && isCloud) location.reload();
});
initialize().catch(error => {
  status.textContent = error.message || '无法读取角色存档。';
  console.error(error);
});
