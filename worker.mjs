const COOKIE = '__Host-dnd_session';
const SESSION_AGE = 7 * 24 * 60 * 60;
const MAX_CARD_BYTES = 1_800_000;
const encoder = new TextEncoder();
const hex = bytes => Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('');
const random = size => hex(crypto.getRandomValues(new Uint8Array(size)));
const hashToken = async token => hex(new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(token))));

function json(value, status = 200, headers = {}) {
  return Response.json(value, { status, headers: {
    'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', ...headers
  } });
}

function fail(status, message) {
  throw json({ error: message }, status);
}

function cookie(token, age) {
  return COOKIE + '=' + token + '; Path=/; Max-Age=' + age + '; HttpOnly; Secure; SameSite=Lax';
}

async function readBody(request, limit) {
  if (!request.headers.get('Content-Type')?.toLowerCase().startsWith('application/json')) {
    fail(415, '请使用 JSON 格式');
  }
  if (!request.body) fail(400, '缺少请求内容');
  const reader = request.body.getReader();
  const decoder = new TextDecoder();
  let body = '';
  let size = 0;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > limit) {
      await reader.cancel();
      fail(413, '文件过大，请缩小角色立绘后重试');
    }
    body += decoder.decode(value, { stream: true });
  }
  try { return JSON.parse(body + decoder.decode()); }
  catch { fail(400, '无法读取 JSON'); }
}

async function passwordHash(password, salt) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(password), 'PBKDF2', false, ['deriveBits']);
  return hex(new Uint8Array(await crypto.subtle.deriveBits({
    name: 'PBKDF2', salt: encoder.encode(salt), iterations: 100000, hash: 'SHA-256'
  }, key, 256)));
}

async function session(db, tokenHash) {
  if (!tokenHash) return null;
  return db.prepare(`
    SELECT users.id, users.username FROM sessions JOIN users ON users.id = sessions.user_id
    WHERE sessions.token_hash = ? AND sessions.expires_at > ?
  `).bind(tokenHash, Date.now()).first();
}

async function signIn(db, request, register, previousTokenHash) {
  const body = await readBody(request, 4096);
  const username = typeof body?.username === 'string' ? body.username.trim() : '';
  const password = body?.password;
  const key = username.normalize('NFKC').toLowerCase();
  if (!/^[\p{L}\p{N}_-]{1,32}$/u.test(key) || typeof password !== 'string' || !password || password.length > 128) {
    fail(400, '用户名限 1–32 个字母、数字、下划线或连字符；密码限 1–128 个字符');
  }
  let user;
  if (register) {
    user = { id: crypto.randomUUID(), username };
    const salt = random(16);
    const hash = await passwordHash(password, salt);
    const result = await db.prepare(`
      INSERT INTO users (id, username, username_key, salt, password_hash) VALUES (?, ?, ?, ?, ?)
      ON CONFLICT(username_key) DO NOTHING
    `).bind(user.id, username, key, salt, hash).run();
    if (!result.meta.changes) fail(409, '用户名已被使用');
  } else {
    const row = await db.prepare('SELECT id, username, salt, password_hash FROM users WHERE username_key = ?').bind(key).first();
    const hash = await passwordHash(password, row?.salt || '00000000000000000000000000000000');
    if (!row || !crypto.subtle.timingSafeEqual(encoder.encode(hash), encoder.encode(row.password_hash))) {
      fail(401, '用户名或密码错误');
    }
    user = { id: row.id, username: row.username };
  }
  const token = random(32);
  await db.batch([
    db.prepare('DELETE FROM sessions WHERE expires_at <= ? OR token_hash = ?').bind(Date.now(), previousTokenHash || ''),
    db.prepare('INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)')
      .bind(await hashToken(token), user.id, Date.now() + SESSION_AGE * 1000)
  ]);
  return json({ user }, register ? 201 : 200, { 'Set-Cookie': cookie(token, SESSION_AGE) });
}

async function characterRequest(db, request, user, id) {
  const method = request.method;
  if (request.headers.get('X-DND-Account') !== user.id) fail(409, '登录账号已变更，请刷新页面后重试');
  if (id && !/^[A-Za-z0-9_-]{1,80}$/.test(id)) fail(404, '找不到角色卡');
  if (method === 'GET') {
    if (!id) {
      const { results } = await db.prepare('SELECT data FROM characters WHERE owner_id = ? ORDER BY updated_at DESC').bind(user.id).all();
      return json(results.map(row => JSON.parse(row.data)));
    }
    const row = await db.prepare('SELECT data FROM characters WHERE owner_id = ? AND sheet_id = ?').bind(user.id, id).first();
    if (!row) fail(404, '找不到角色卡');
    return json(JSON.parse(row.data));
  }
  if (method === 'DELETE' && id) {
    const result = await db.prepare('DELETE FROM characters WHERE owner_id = ? AND sheet_id = ?').bind(user.id, id).run();
    if (!result.meta.changes) fail(404, '找不到角色卡');
    return json({ ok: true });
  }
  if ((method === 'POST' && !id) || (method === 'PUT' && id)) {
    const data = await readBody(request, MAX_CARD_BYTES);
    if (data?.schema !== 'dnd-character-sheet' || data.version !== 9 ||
        typeof data.sheetId !== 'string' || !/^[A-Za-z0-9_-]{1,80}$/.test(data.sheetId) ||
        (id && id !== data.sheetId) || !data.identity || typeof data.identity !== 'object' ||
        Array.isArray(data.identity)) fail(400, '角色卡必须使用 Character JSON v9');
    data.exportedAt = new Date().toISOString();
    const serialized = JSON.stringify(data);
    if (method === 'POST') {
      const result = await db.prepare(`
        INSERT INTO characters (owner_id, sheet_id, updated_at, data) VALUES (?, ?, ?, ?)
        ON CONFLICT(owner_id, sheet_id) DO NOTHING
      `).bind(user.id, data.sheetId, data.exportedAt, serialized).run();
      if (!result.meta.changes) fail(409, '该角色卡已存在');
      return json({ ok: true }, 201);
    }
    const result = await db.prepare('UPDATE characters SET updated_at = ?, data = ? WHERE owner_id = ? AND sheet_id = ?')
      .bind(data.exportedAt, serialized, user.id, id).run();
    if (!result.meta.changes) fail(404, '找不到角色卡');
    return json({ ok: true });
  }
  fail(405, '此操作不受支持');
}

function spellSearchKey(value) {
  return value.normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
}

async function searchSpells(request, db) {
  if (request.method !== 'GET') fail(405, '此操作不受支持');
  const query = new URL(request.url).searchParams.get('q') || '';
  if (query.length > 80) fail(400, '法术名称查询过长');
  const key = spellSearchKey(query);
  if (!key) return json({ spells: [] });
  if (!db) fail(503, '测试法术库尚未配置');

  const ordered = '%' + [...key].join('%') + '%';
  const { results } = await db.prepare(`
    WITH search(key, pattern) AS (VALUES (?, ?))
    SELECT id, name, english_name, ruleset, source, source_type, level, school,
           verbal, somatic, material, concentration, ritual, duration, description
    FROM spells CROSS JOIN search
    WHERE name_key LIKE search.pattern OR english_key LIKE search.pattern
    ORDER BY CASE
      WHEN name_key = search.key OR english_key = search.key THEN 0
      WHEN instr(name_key, search.key) = 1 OR instr(english_key, search.key) = 1 THEN 1
      WHEN instr(name_key, search.key) > 0 OR instr(english_key, search.key) > 0 THEN 2
      ELSE 3
    END, name, ruleset DESC, id
    LIMIT 8
  `).bind(key, ordered).all();

  return json({ spells: results.map(row => ({
    id: row.id,
    name: row.name,
    englishName: row.english_name,
    ruleset: row.ruleset,
    source: row.source,
    sourceType: row.source_type,
    level: row.level,
    school: row.school,
    components: {
      verbal: Boolean(row.verbal), somatic: Boolean(row.somatic), material: Boolean(row.material)
    },
    concentration: Boolean(row.concentration),
    ritual: Boolean(row.ritual),
    duration: row.duration,
    description: row.description
  })) });
}

async function handleApi(request, env, path) {
  try {
    if (path.length === 2 && path[0] === 'rules' && path[1] === 'spells') {
      return await searchSpells(request, env.RULES_DB);
    }
    const db = env.DB;
    if (!db) fail(503, '云端存档尚未配置');
    const url = new URL(request.url);
    const method = request.method;
    if (method !== 'GET' && request.headers.get('Origin') !== url.origin) fail(403, '请求来源无效');

    const token = request.headers.get('Cookie')?.match(/(?:^|;\s*)__Host-dnd_session=([a-f0-9]{64})(?:;|$)/)?.[1];
    const tokenHash = token ? await hashToken(token) : null;
    const [resource, id, ...rest] = path;
    if (!rest.length && !id && method === 'POST') {
      if (resource === 'register' || resource === 'login') return await signIn(db, request, resource === 'register', tokenHash);
      if (resource === 'logout') {
        if (tokenHash) await db.prepare('DELETE FROM sessions WHERE token_hash = ?').bind(tokenHash).run();
        return json({ ok: true }, 200, { 'Set-Cookie': cookie('', 0) });
      }
    }
    const user = await session(db, tokenHash);
    if (!id && resource === 'session' && method === 'GET') return json({ user });
    if (!rest.length && resource === 'characters') {
      if (!user) fail(401, '请先登录');
      return await characterRequest(db, request, user, id);
    }
    fail(404, '找不到此接口');
  } catch (error) {
    if (error instanceof Response) return error;
    console.error(error);
    return json({ error: '云端服务暂时不可用，请稍后重试' }, 500);
  }
}

export default {
  fetch(request, env) {
    const { pathname } = new URL(request.url);
    if (pathname === '/api' || pathname.startsWith('/api/')) {
      const path = pathname.slice('/api/'.length).split('/');
      return handleApi(request, env, path);
    }
    return env.ASSETS.fetch(request);
  }
};
