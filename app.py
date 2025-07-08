from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import threading
import subprocess

app = Flask(__name__)

# 🔧 Configuration MySQL (à adapter)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/pfedb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 🔌 Connexion à la base
db = SQLAlchemy(app)

# 🧱 Modèle utilisateur
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)

# ⚙️ Créer la table automatiquement + ajouter un utilisateur test
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin = User(username="admin", password="1234")
        db.session.add(admin)
        db.session.commit()

# 🚀 Fonction pour lancer Streamlit
def run_streamlit():
    subprocess.call(["streamlit", "run", "yvideo_voice_converter.py"])

# 🔐 Route de login
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            # Lancer Streamlit dans un thread séparé
            threading.Thread(target=run_streamlit).start()
            return redirect("http://localhost:8501")
        else:
            error = "Nom d'utilisateur ou mot de passe incorrect."

    return render_template('index.html', error=error)

# ▶️ Lancer Flask
if __name__ == '__main__':
    app.run(debug=True)
from flask import jsonify

@app.route('/chatbot', methods=['POST'])
def chatbot():
    user_message = request.json['message'].lower()

    if "hello" in user_message:
        return jsonify(response="Hello! I'm your assistant. How can I help you?")
    elif "password" in user_message:
        return jsonify(response="Click 'Forgot Password' to reset it.")
    elif "signup" in user_message:
        return jsonify(response="Click on the Signup button to create your account.")
    else:
        return jsonify(response="I'm here to help. Can you rephrase your question?")
        
