import os
from flask import Flask, jsonify
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'mudar_para_uma_chave_secreta_mais_forte'
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

MASTER_ADMIN = 'Victor'

users = {
    'admin': {
        'password': generate_password_hash('admin123'),
        'fichas': 0,
        'is_admin': True,
        'protected': False,
        'public': False,
        'plain': 'admin123'
    },
    MASTER_ADMIN: {
        'password': generate_password_hash('jojo01023'),
        'fichas': 0,
        'is_admin': True,
        'protected': True,
        'public': False,
        'plain': 'jojo01023'
    }
}

# pending password change requests: username -> hashed_new_password
pending_password_changes = {}

LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a1a1a">
    <title>Login</title>
    <style>
        body { background: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding-top: 100px; }
        .card { display: inline-block; padding: 30px; background: #242424; border-radius: 16px; box-shadow: 0 0 30px rgba(0,0,0,0.4); }
        input { width: 280px; padding: 14px 16px; margin: 8px 0; border-radius: 10px; border: 1px solid #444; background: #1a1a1a; color: white; }
        button { width: 100%; background: #00ff66; border: none; color: black; padding: 16px; font-size: 18px; font-weight: bold; border-radius: 14px; cursor: pointer; }
        .error { color: #ff7f7f; margin-top: 16px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Login</h2>
        <form method="POST">
            <input name="username" placeholder="Usuário" required>
            <input name="password" type="password" placeholder="Senha" required>
            <button type="submit">Entrar</button>
        </form>
        <div style="margin-top:10px; text-align:center;"><a href="/forgot_password" style="color:#00ff66; text-decoration:none;">Esqueci a senha</a></div>
        {% if error %}
            <div class="error">{{ error }}</div>
        {% endif %}
    </div>
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(()=>{});
    }
    </script>
</body>
</html>
"""

INDEX_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a1a1a">
    <title>Painel de Fichas</title>
    <style>
        body { background: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding-top: 60px; }
        .container { display: inline-block; text-align: left; background: #242424; padding: 30px; border-radius: 18px; box-shadow: 0 0 30px rgba(0,0,0,0.4); min-width: 320px; }
        .field { margin: 18px 0; }
        .field label { display: block; margin-bottom: 8px; }
        .field input { width: 100%; padding: 14px; font-size: 16px; border-radius: 12px; border: 1px solid #444; background: #1a1a1a; color: white; }
        .btn { background: #00ff66; border: none; color: black; padding: 16px 28px; font-size: 18px; font-weight: bold; border-radius: 14px; cursor: pointer; }
        .links { margin-top: 20px; }
        .links a { color: #00ff66; text-decoration: none; margin: 0 8px; }
        .message { margin-top: 18px; color: #a8ff94; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Bem-vindo, {{ username }}</h2>
        <p>Total de fichas injetadas: <strong>{{ fichas }}</strong></p>
        <form method="POST">
            <div class="field">
                <label for="count">Quantas fichas deseja injetar?</label>
                <input id="count" name="count" type="number" min="1" max="100" value="1" required>
            </div>
            <button type="submit" class="btn">Injetar Crédito</button>
        </form>
        <div class="links">
            {% if is_admin %}<a href="/admin">Painel Admin</a>{% endif %}
            <a href="/change_password">Solicitar troca de senha</a>
            <a href="/logout">Sair</a>
        </div>
        {% if visible_users %}
            <div class="message">
                <strong>Fichas visíveis para você:</strong>
                <ul>
                {% for other in visible_users %}
                    <li>{{ other.name }}: {{ other.fichas }}</li>
                {% endfor %}
                </ul>
            </div>
        {% endif %}
        {% if message %}
            <div class="message">{{ message }}</div>
        {% endif %}
    </div>
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(()=>{});
    }
    </script>
</body>
</html>
"""

CHANGE_PASSWORD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a1a1a">
    <title>Solicitar Troca de Senha</title>
    <style>
        body { background: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding-top: 100px; }
        .card { display: inline-block; padding: 30px; background: #242424; border-radius: 16px; }
        input { width: 280px; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #444; background: #1a1a1a; color: white; }
        button { width: 100%; background: #00ff66; border: none; color: black; padding: 12px; font-size: 16px; border-radius: 10px; cursor: pointer; }
        .message { margin-top: 12px; color: #a8ff94; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Solicitar troca de senha</h2>
        <form method="POST">
            <input name="current_password" type="password" placeholder="Senha atual" required>
            <input name="new_password" type="password" placeholder="Nova senha" required>
            <button type="submit">Enviar solicitação</button>
        </form>
        {% if message %}<div class="message">{{ message }}</div>{% endif %}
    </div>
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(()=>{});
    }
    </script>
</body>
</html>
"""

FORGOT_PASSWORD_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a1a1a">
    <title>Esqueci a Senha</title>
    <style>
        body { background: #1a1a1a; color: white; font-family: sans-serif; text-align: center; padding-top: 100px; }
        .card { display: inline-block; padding: 30px; background: #242424; border-radius: 16px; }
        input { width: 280px; padding: 12px; margin: 8px 0; border-radius: 8px; border: 1px solid #444; background: #1a1a1a; color: white; }
        button { width: 100%; background: #00ff66; border: none; color: black; padding: 12px; font-size: 16px; border-radius: 10px; cursor: pointer; }
        .message { margin-top: 12px; color: #a8ff94; }
    </style>
</head>
<body>
    <div class="card">
        <h2>Solicitar troca de senha (esqueci a senha)</h2>
        <form method="POST">
            <input name="username" placeholder="Nome de usuário" required>
            <input name="new_password" type="password" placeholder="Nova senha desejada" required>
            <button type="submit">Enviar solicitação</button>
        </form>
        {% if message %}<div class="message">{{ message }}</div>{% endif %}
    </div>
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(()=>{});
    }
    </script>
</body>
</html>
"""

ADMIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#1a1a1a">
    <title>Painel de Administração</title>
    <style>
        body { background: #1a1a1a; color: white; font-family: sans-serif; padding: 40px; }
        h1, h2 { margin-bottom: 16px; }
        .card { background: #242424; padding: 28px; border-radius: 18px; box-shadow: 0 0 30px rgba(0,0,0,0.4); margin-bottom: 24px; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { padding: 12px 14px; border-bottom: 1px solid #333; }
        th { text-align: left; }
        .btn { background: #00ff66; border: none; color: black; padding: 12px 20px; font-size: 16px; border-radius: 12px; cursor: pointer; }
        .danger { background: #ff4f4f; }
        input { width: 100%; padding: 12px; margin: 8px 0; border-radius: 12px; border: 1px solid #444; background: #1a1a1a; color: white; }
        label { display: block; margin: 10px 0; font-size: 14px; }
        .small { font-size: 14px; color: #bbb; }
        .message { margin-top: 16px; color: #a8ff94; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Painel de Administração</h1>
        <p>Administrador conectado: <strong>{{ username }}</strong></p>
        <a class="btn" href="/">Voltar ao painel</a>
        <a class="btn" href="/logout">Sair</a>
    </div>

    <div class="card">
        <h2>Perfis existentes</h2>
        <table>
            <thead>
                <tr><th>Usuário</th><th>Admin</th><th>Fichas Injetadas</th><th>Senha</th><th>Mostrar fichas</th><th>Ação</th></tr>
            </thead>
            <tbody>
                {% for user in users %}
                    <tr>
                        <td>{{ user.name }}</td>
                        <td>{{ 'Sim' if user.is_admin else 'Não' }}</td>
                        <td>{{ user.fichas }}</td>
                        <td>{% if is_master %}{{ user.plain }}{% else %}***{% endif %}</td>
                        <td>
                            <form method="POST" action="/admin/visibility" style="display:inline-block;">
                                <input type="hidden" name="username" value="{{ user.name }}">
                                <input type="checkbox" name="public" value="1" {% if user.public %}checked{% endif %} onchange="this.form.submit()" {% if user.protected %}disabled{% endif %}>
                            </form>
                        </td>
                                <td>
                                    {% if is_master %}
                                        <form method="POST" action="/admin/set_password" style="display:inline;">
                                            <input type="hidden" name="username" value="{{ user.name }}">
                                            <input name="new_password" type="password" placeholder="Nova senha" style="width:140px; padding:6px; margin-right:6px;">
                                            <button type="submit" class="btn">Setar senha</button>
                                        </form>
                                    {% endif %}
                                    {% if user.name != username and not user.protected %}
                                        <form method="POST" action="/admin/delete" style="display:inline; margin-left:8px;">
                                            <input type="hidden" name="username" value="{{ user.name }}">
                                            <button type="submit" class="btn danger">Excluir</button>
                                        </form>
                                    {% elif user.protected %}
                                        <span class="small">Perfil protegido</span>
                                    {% else %}
                                        <span class="small">Usuário atual</span>
                                    {% endif %}
                                </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {% if pending_requests %}
    <div class="card">
        <h2>Solicitações de troca de senha (pendentes)</h2>
        <table>
            <thead>
                <tr><th>Usuário</th><th>Senha solicitada</th><th>Ações</th></tr>
            </thead>
            <tbody>
                {% for req in pending_requests %}
                <tr>
                    <td>{{ req.name }}</td>
                    <td>{% if is_master %}{{ req.plain }}{% else %}***{% endif %}</td>
                    <td>
                        {% if is_master %}
                        <form method="POST" action="/admin/approve_password" style="display:inline;">
                            <input type="hidden" name="username" value="{{ req.name }}">
                            <button type="submit" class="btn">Aprovar</button>
                        </form>
                        {% endif %}
                        <form method="POST" action="/admin/deny_password" style="display:inline; margin-left:8px;">
                            <input type="hidden" name="username" value="{{ req.name }}">
                            <button type="submit" class="btn danger">Recusar</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {% endif %}

    <div class="card">
        <h2>Criar novo perfil</h2>
        <form method="POST" action="/admin/create">
            <input name="new_username" placeholder="Nome de usuário" required>
            <input name="new_password" type="password" placeholder="Senha" required>
            <label><input type="checkbox" name="is_admin"> Perfil administrador</label>
            <button type="submit" class="btn">Criar perfil</button>
        </form>
        {% if message %}
            <div class="message">{{ message }}</div>
        {% endif %}
    </div>
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(()=>{});
    }
    </script>
</body>
</html>
"""

@app.route('/sw.js')
def service_worker():
    return flask.send_from_directory('static', 'sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    return flask.send_from_directory('static', 'manifest.json', mimetype='application/json')

@app.route('/icon-192.png')
def icon_192():
    return flask.send_from_directory('static', 'icon-192.png', mimetype='image/png')

@app.route('/icon-512.png')
def icon_512():
    return flask.send_from_directory('static', 'icon-512.png', mimetype='image/png')


def get_current_username():
    return flask.session.get('username')


def user_is_admin():
    username = get_current_username()
    return bool(username and users.get(username, {}).get('is_admin'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if get_current_username():
        return flask.redirect(flask.url_for('index'))

    error = None
    if flask.request.method == 'POST':
        username = flask.request.form.get('username', '').strip()
        password = flask.request.form.get('password', '')
        user = users.get(username)

        if not user or not check_password_hash(user['password'], password):
            error = 'Usuário ou senha inválidos.'
        else:
            flask.session['username'] = username
            return flask.redirect(flask.url_for('index'))

    return flask.render_template_string(LOGIN_PAGE, error=error)


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    username = get_current_username()
    if not username:
        return flask.redirect(flask.url_for('login'))

    message = None
    if flask.request.method == 'POST':
        current = flask.request.form.get('current_password', '')
        new = flask.request.form.get('new_password', '')
        user = users.get(username)
        if not user or not check_password_hash(user['password'], current):
            message = 'Senha atual incorreta.'
        else:
            # store hashed new password and plaintext in pending requests for admin approval
            pending_password_changes[username] = {'hash': generate_password_hash(new), 'plain': new}
            message = 'Solicitação enviada: aguarde aprovação do administrador mestre.'

    return flask.render_template_string(CHANGE_PASSWORD_PAGE, message=message)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    message = None
    if flask.request.method == 'POST':
        uname = flask.request.form.get('username', '').strip()
        new = flask.request.form.get('new_password', '')
        if not uname or not new:
            message = 'Nome de usuário e nova senha são necessários.'
        elif uname not in users:
            message = 'Usuário não encontrado.'
        else:
            pending_password_changes[uname] = {'hash': generate_password_hash(new), 'plain': new}
            message = 'Solicitação enviada: aguarde aprovação do administrador mestre.'

    return flask.render_template_string(FORGOT_PASSWORD_PAGE, message=message)


@app.route('/logout')
def logout():
    flask.session.pop('username', None)
    return flask.redirect(flask.url_for('login'))


@app.route('/')
def index():
    username = get_current_username()
    if not username:
        return flask.redirect(flask.url_for('login'))

    user = users.get(username)
    visible_users = [
        {'name': name, 'fichas': data['fichas']}
        for name, data in users.items()
        if name != username and data.get('public')
    ]
    return flask.render_template_string(
        INDEX_PAGE,
        username=username,
        fichas=user['fichas'],
        is_admin=user['is_admin'],
        visible_users=visible_users,
        message=flask.request.args.get('message')
    )


@app.route('/', methods=['POST'])
def colocar_ficha():
    username = get_current_username()
    if not username:
        return flask.redirect(flask.url_for('login'))

    user = users.get(username)
    count = flask.request.form.get('count', '1')
    try:
        count = int(count)
    except ValueError:
        count = 1
    count = max(1, min(count, 100))

    user['fichas'] += count

    message = f'{count} ficha(s) injetada(s) para {username}.'
    visible_users = [
        {'name': name, 'fichas': data['fichas']}
        for name, data in users.items()
        if name != username and data.get('public')
    ]
    return flask.render_template_string(
        INDEX_PAGE,
        username=username,
        fichas=user['fichas'],
        is_admin=user['is_admin'],
        visible_users=visible_users,
        message=message
    )


@app.route('/admin')
def admin():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    user_list = []
    for name, data in users.items():
        user_list.append({
            'name': name,
            'is_admin': data['is_admin'],
            'fichas': data['fichas'],
            'protected': data.get('protected', False),
            'public': data.get('public', False),
            'plain': data.get('plain') if username == MASTER_ADMIN else None
        })

    pending_list = []
    for name, data in pending_password_changes.items():
        pending_list.append({'name': name, 'plain': data.get('plain') if username == MASTER_ADMIN else None})
    return flask.render_template_string(
        ADMIN_PAGE,
        username=username,
        users=user_list,
        pending_requests=pending_list,
        is_master=(username == MASTER_ADMIN),
        message=flask.request.args.get('message')
    )


@app.route('/admin/visibility', methods=['POST'])
def admin_visibility():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    target = flask.request.form.get('username', '').strip()
    if target not in users:
        return flask.redirect(flask.url_for('admin', message='Usuário não encontrado.'))

    users[target]['public'] = bool(flask.request.form.get('public'))
    return flask.redirect(flask.url_for('admin', message=f'Visibilidade atualizada para {target}.'))


@app.route('/admin/approve_password', methods=['POST'])
def admin_approve_password():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    # only the MASTER_ADMIN can approve password changes
    if username != MASTER_ADMIN:
        return flask.redirect(flask.url_for('admin', message='Apenas o administrador mestre pode aprovar trocas de senha.'))

    target = flask.request.form.get('username', '').strip()
    if target not in pending_password_changes:
        return flask.redirect(flask.url_for('admin', message='Solicitação não encontrada.'))

    pending = pending_password_changes.pop(target)
    users[target]['password'] = pending.get('hash')
    users[target]['plain'] = pending.get('plain')
    return flask.redirect(flask.url_for('admin', message=f'Senha de {target} atualizada com sucesso.'))


@app.route('/admin/deny_password', methods=['POST'])
def admin_deny_password():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    # both admins can deny, but only master approves
    target = flask.request.form.get('username', '').strip()
    if target not in pending_password_changes:
        return flask.redirect(flask.url_for('admin', message='Solicitação não encontrada.'))

    pending_password_changes.pop(target, None)
    return flask.redirect(flask.url_for('admin', message=f'Solicitação de {target} recusada.'))



@app.route('/admin/create', methods=['POST'])
def admin_create():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    new_username = flask.request.form.get('new_username', '').strip()
    new_password = flask.request.form.get('new_password', '')
    is_admin_flag = bool(flask.request.form.get('is_admin'))

    if not new_username or not new_password:
        return flask.redirect(flask.url_for('admin', message='Nome e senha são obrigatórios.'))

    if new_username == MASTER_ADMIN:
        return flask.redirect(flask.url_for('admin', message=f'Usuário {MASTER_ADMIN} é reservado e não pode ser criado.'))

    if new_username in users:
        return flask.redirect(flask.url_for('admin', message='Usuário já existe.'))

    users[new_username] = {
        'password': generate_password_hash(new_password),
        'fichas': 0,
        'is_admin': is_admin_flag,
        'protected': False,
        'public': False
    }
    return flask.redirect(flask.url_for('admin', message=f'Perfil {new_username} criado com sucesso.'))


@app.route('/admin/set_password', methods=['POST'])
def admin_set_password():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    # only master admin can directly set passwords
    if username != MASTER_ADMIN:
        return flask.redirect(flask.url_for('admin', message='Apenas o administrador mestre pode alterar senhas diretamente.'))

    target = flask.request.form.get('username', '').strip()
    new_password = flask.request.form.get('new_password', '')
    if not target or not new_password:
        return flask.redirect(flask.url_for('admin', message='Usuário e nova senha são necessários.'))
    if target not in users:
        return flask.redirect(flask.url_for('admin', message='Usuário não encontrado.'))

    users[target]['password'] = generate_password_hash(new_password)
    users[target]['plain'] = new_password
    # if there was a pending request, clear it
    pending_password_changes.pop(target, None)
    return flask.redirect(flask.url_for('admin', message=f'Senha de {target} alterada pelo administrador mestre.'))


@app.route('/admin/delete', methods=['POST'])
def admin_delete():
    username = get_current_username()
    if not username or not user_is_admin():
        return flask.redirect(flask.url_for('login'))

    target = flask.request.form.get('username', '').strip()
    if target == username:
        return flask.redirect(flask.url_for('admin', message='Não é possível excluir o usuário conectado.'))
    if target not in users:
        return flask.redirect(flask.url_for('admin', message='Usuário não encontrado.'))
    if users[target].get('protected'):
        return flask.redirect(flask.url_for('admin', message=f'O perfil {target} é protegido e não pode ser excluído.'))

    users.pop(target, None)
    return flask.redirect(flask.url_for('admin', message=f'Perfil {target} excluído.'))


if __name__ == '__main__':
    host = os.environ.get('FICHA_HOST', '0.0.0.0')
    port = int(os.environ.get('FICHA_PORT', '8080'))
    debug = os.environ.get('FICHA_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host=host, port=port, debug=debug)
    app.run(host=host, port=port, debug=debug)