'use strict';

const CharacterDB = (() => {
  let connection;
  function open() {
    if (!connection) {
      connection = new Promise((resolve, reject) => {
        const request = indexedDB.open('dnd-character-website', 1);
        request.onupgradeneeded = () => request.result.createObjectStore('characters', { keyPath: 'sheetId' });
        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
      }).catch(error => { connection = undefined; throw error; });
    }
    return connection;
  }

  async function transaction(mode, action) {
    const db = await open();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('characters', mode);
      const result = action(tx.objectStore('characters'));
      tx.oncomplete = () => resolve(result?.result);
      tx.onabort = () => reject(tx.error || new Error('存档操作已取消'));
    });
  }

  return {
    get: id => transaction('readonly', store => store.get(id)),
    getAll: () => transaction('readonly', store => store.getAll()),
    create: data => transaction('readwrite', store => store.add(data)),
    update: data => transaction('readwrite', store => {
      const request = store.getKey(data.sheetId);
      request.onsuccess = () => {
        if (request.result === undefined) store.transaction.abort();
        else store.put(data);
      };
    }),
    delete: id => transaction('readwrite', store => store.delete(id))
  };
})();
