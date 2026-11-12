'use strict';

const Cloud = (() => {
  async function request(path, { method = 'GET', data, user } = {}) {
    const headers = {};
    if (data !== undefined) headers['Content-Type'] = 'application/json';
    if (user) headers['X-DND-Account'] = user.id;
    const response = await fetch('/api/' + path, {
      method, headers, body: data === undefined ? undefined : JSON.stringify(data),
      credentials: 'same-origin', cache: 'no-store'
    });
    const result = await response.json().catch(() => null);
    if (!response.ok || !result) throw new Error(result?.error || '无法连接云端服务');
    return result;
  }

  return {
    async user() { return (await request('session')).user; },
    async login(data, register) {
      return (await request(register ? 'register' : 'login', { method: 'POST', data })).user;
    },
    logout() { return request('logout', { method: 'POST' }); },
    cards(user) {
      const path = id => 'characters/' + encodeURIComponent(id);
      return {
        getAll: () => request('characters', { user }),
        get: id => request(path(id), { user }),
        create: data => request('characters', { method: 'POST', data, user }),
        update: data => request(path(data.sheetId), { method: 'PUT', data, user }),
        delete: id => request(path(id), { method: 'DELETE', user })
      };
    }
  };
})();
