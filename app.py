from flask import (Flask, render_template, request, redirect, 
    url_for, flash)
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

app = Flask(__name__)

app.config['SECRET_KEY'] = 'IFSC2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dbcontatos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# Modelo do usuário
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    contatos = db.relationship('Contato', backref='user', lazy=True)

# Modelo do contato
class Contato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    celular = db.Column(db.String(150), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    mensagens = db.relationship('Mensagem', backref='contato', lazy=True)
    
# Modelo da mensagem
class Mensagem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(150), nullable=False)
    mensagem = db.Column(db.String(150), nullable=False)
    data = db.Column(db.DateTime, nullable=False)
    contato_id = db.Column(db.Integer, db.ForeignKey('contato.id'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('listar_contatos'))
    return redirect(url_for('login'))

@app.route('/contatos')
@login_required
def listar_contatos():
    contatos = current_user.contatos
    return render_template('contatos.html', contatos=contatos)

@app.route('/contatos/novo', methods=['GET', 'POST'])
@login_required
def novo_contato():
    if request.method == 'POST':
        name = request.form.get('nome')
        if len(name) > 2:
            email = request.form.get('email') or ''
            celular = request.form.get('celular') or ''
            novo_contato = Contato(
                name=name, 
                email=email, 
                celular=celular,
                user_id=current_user.id
            ) 
            db.session.add(novo_contato)
            db.session.commit()
            flash('Contato adicionado com sucesso!', 'success')
            return redirect(url_for('listar_contatos'))
    return render_template('novo_contato.html')

@app.route('/contatos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_contato(id):
    contato = Contato.query.get(id)
    
    if not contato or contato.user_id != current_user.id:
        flash('Contato não encontrado ou você não tem permissão para editá-lo.', 'danger')
        return redirect(url_for('listar_contatos'))
    
    if request.method == 'POST':
        contato.name = request.form.get('nome')
        contato.email = request.form.get('email')
        contato.celular = request.form.get('celular')
        db.session.commit()
        flash('Contato atualizado com sucesso!', 'success')
        return redirect(url_for('listar_contatos'))
    
    return render_template('editar_contato.html', contato=contato)

@app.route('/contatos/<int:id>/excluir', methods=['POST'])
@login_required
def excluir_contato(id):
    contato = Contato.query.get(id)
    
    if contato and contato.user_id == current_user.id:
        db.session.delete(contato)
        db.session.commit()
        flash('Contato excluído com sucesso!', 'success')
    
    return redirect(url_for('listar_contatos'))


@app.route('/contatos/<int:id>/mensagens', methods=['GET', 'POST'])
@login_required
def mensagens_contato(id):
    contato = Contato.query.get(id)
    if not contato or contato.user_id != current_user.id:
        flash('Contato não encontrado ou você não tem permissão para acessá-lo.', 'danger')
        return redirect(url_for('listar_contatos'))
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        mensagem_texto = request.form.get('mensagem')
        
        if titulo and mensagem_texto:
            nova_mensagem = Mensagem(
                titulo=titulo,
                mensagem=mensagem_texto,
                data=datetime.now(),
                contato_id=contato.id
            )
            db.session.add(nova_mensagem)
            db.session.commit()
            flash('Mensagem enviada com sucesso!', 'success')
            return redirect(url_for('mensagens_contato', id=contato.id))

    mensagens = Mensagem.query.filter_by(contato_id=contato.id).order_by(Mensagem.data.desc()).all()
    
    return render_template('msg.html', contato=contato, mensagens=mensagens)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Usuário não existe!', 'danger')
            return redirect(url_for('login'))
        if not check_password_hash(user.password, password):
            flash("Senha inválida!", 'danger')
            return redirect(url_for('login'))
        
        login_user(user)
        flash('Login realizado com sucesso!', 'success')
        return redirect(url_for('listar_contatos'))
        
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password1 = request.form['password1']
        password2 = request.form['password2']
        erros = []
        
        if len(name) < 2:
            erros.append('Nome deve ter pelo menos 2 caracteres')
        if email.find('@') == -1:
            erros.append('Email inválido')
        if len(password1) < 8:
            erros.append('A senha deve ter pelo menos 8 caracteres')
        if password1 != password2:
            erros.append('As senhas devem ser iguais')
        
        if len(erros) > 0:
            return render_template('signup.html', erros=erros, name=name, email=email)
        else:
            if User.query.filter_by(email=email).first():
                flash('Email já cadastrado!', 'danger')
                return redirect(url_for('signup'))
                
            senha_hash = generate_password_hash(password1)
            user = User(name=name, email=email, password=senha_hash)
            db.session.add(user)
            db.session.commit()
            
            login_user(user)
            flash('Conta criada com sucesso!', 'success')
            return redirect(url_for('listar_contatos'))
    
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi deslogado com sucesso.', 'info')
    return redirect(url_for('login'))

def create_tables():
    with app.app_context():
        db.create_all()

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)