'use strict';

const form = document.querySelector('#account-form');
const signedIn = document.querySelector('#signed-in');
const accountStatus = document.querySelector('#account-status');
const logout = document.querySelector('#logout');

function showAccount(user) {
  form.hidden = Boolean(user);
  signedIn.hidden = !user;
  accountStatus.textContent = user ? '已登录：' + user.username : '使用用户名和密码登录或注册。';
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  const register = event.submitter?.value === 'register';
  const data = Object.fromEntries(new FormData(form));
  const buttons = [...form.querySelectorAll('button')];
  buttons.forEach(button => { button.disabled = true; });
  try {
    await Cloud.login(data, register);
    form.reset();
    location.replace('characters.html?storage=cloud');
  } catch (error) {
    accountStatus.textContent = error.message;
  } finally {
    buttons.forEach(button => { button.disabled = false; });
  }
});

logout.onclick = async () => {
  logout.disabled = true;
  try {
    await Cloud.logout();
    showAccount(null);
  } catch (error) { accountStatus.textContent = error.message; }
  finally { logout.disabled = false; }
};

window.addEventListener('pageshow', () => {
  Cloud.user().then(showAccount).catch(error => { accountStatus.textContent = error.message; });
});
