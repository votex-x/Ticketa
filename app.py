// App logic: login via Discord (implicit grant), then post commands to Firebase Realtime DB
const app = firebase.initializeApp(FIREBASE_CONFIG);
const db = firebase.database();

const loginBtn = document.getElementById('btn-login');
const logoutBtn = document.getElementById('btn-logout');
const userInfo = document.getElementById('user-info');
const avatar = document.getElementById('avatar');
const usernameSpan = document.getElementById('username');
const formSection = document.getElementById('form-section');
const logs = document.getElementById('logs');

function addLog(text){
  const p = document.createElement('div');
  p.textContent = text;
  logs.prepend(p);
}

function parseHash() {
  // Parse access token from OAuth implicit redirect (fragment)
  const hash = window.location.hash.substring(1);
  const params = new URLSearchParams(hash);
  const token = params.get('access_token');
  if (token) {
    sessionStorage.setItem('discord_token', token);
    // remove fragment for cleanliness
    history.replaceState(null, '', window.location.pathname + window.location.search);
  }
}

async function getDiscordUser(token){
  const resp = await fetch('https://discord.com/api/users/@me', { headers: { Authorization: 'Bearer ' + token } });
  if (!resp.ok) throw new Error('Discord user fetch failed: ' + resp.status);
  return await resp.json();
}

async function onLogin() {
  const token = sessionStorage.getItem('discord_token');
  if (!token) {
    // start implicit OAuth flow
    const scopes = encodeURIComponent('identify email guilds');
    const url = `https://discord.com/api/oauth2/authorize?response_type=token&client_id=${DISCORD_CLIENT_ID}&scope=${scopes}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}`;
    window.location.href = url;
    return;
  }
  try {
    const user = await getDiscordUser(token);
    avatar.src = `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png`;
    usernameSpan.textContent = user.username + '#' + user.discriminator;
    userInfo.style.display = 'inline-flex';
    formSection.style.display = 'block';
    addLog('Logado como ' + user.username);
  } catch (e) {
    console.error(e);
    addLog('Erro ao obter usuário Discord. Faça login novamente.');
    sessionStorage.removeItem('discord_token');
  }
}

logoutBtn.addEventListener('click', () => {
  sessionStorage.removeItem('discord_token');
  userInfo.style.display = 'none';
  formSection.style.display = 'none';
  addLog('Desconectado.');
});

loginBtn.addEventListener('click', onLogin);

// on load, parse hash (if returned from Discord)
parseHash();
// if token exists, auto login
if (sessionStorage.getItem('discord_token')) onLogin();

document.getElementById('btn-create').addEventListener('click', async () => {
  try {
    const token = sessionStorage.getItem('discord_token');
    if (!token) return addLog('Faça login primeiro.');
    const user = await getDiscordUser(token);
    const guildId = document.getElementById('guildId').value.trim();
    if (!guildId) return addLog('Informe o Guild ID onde o bot está instalado.');
    const payload = {
      action: 'create_ticket',
      requester_id: user.id,
      channel_name: document.getElementById('channelName').value || undefined,
      category_id: document.getElementById('categoryId').value || undefined,
      topic: document.getElementById('topic').value || undefined,
      embed: {
        title: document.getElementById('embedTitle').value || undefined,
        description: document.getElementById('embedDesc').value || undefined,
        color: document.getElementById('embedColor').value || undefined,
        thumbnail: document.getElementById('embedThumb').value || undefined,
        image: document.getElementById('embedImage').value || undefined,
        footer: document.getElementById('embedFooter').value || undefined,
        fields: []
      },
      created_at: Date.now()
    };
    // parse fields JSON if provided
    const fieldsText = document.getElementById('embedFields').value.trim();
    if (fieldsText) {
      try {
        payload.embed.fields = JSON.parse(fieldsText);
      } catch (e) {
        return addLog('Embed fields JSON inválido.');
      }
    }
    // push command into Firebase Realtime DB under /commands/<guildId>/<uuid>
    const cmdId = Math.random().toString(36).slice(2,10);
    const path = `/commands/${guildId}/${cmdId}`;
    await firebase.database().ref(path).set(payload);
    addLog('Pedido enviado: ' + cmdId);
  } catch (e) {
    console.error(e);
    addLog('Erro ao enviar pedido: ' + e.message);
  }
});
