import os
import sqlite3
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from functools import wraps
from datetime import datetime, timedelta
import re
import click

# Configuration de l'application
app = Flask(__name__)
CORS(app)  # Permet les requêtes cross-origin
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['DATABASE'] = os.environ.get('DATABASE', 'ventes.db')

# Limiter pour prévenir les attaques par force brute
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Fonctions pour la base de données
def get_db():
    """Connexion à la base de données."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Fermeture de la connexion à la base de données."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialisation de la base de données."""
    with app.app_context():
        db = get_db()
        # Création des tables directement dans le code
        db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user'
            );
            
            CREATE TABLE IF NOT EXISTS ventes (
                numProduit INTEGER PRIMARY KEY AUTOINCREMENT,
                design TEXT NOT NULL,
                prix REAL NOT NULL,
                quantite INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        db.commit()

# Commande CLI pour initialiser la base de données
@app.cli.command('init-db')
def init_db_command():
    """Commande pour initialiser la base de données."""
    init_db()
    click.echo('Base de données initialisée.')

def query_db(query, args=(), one=False):
    """Exécute une requête SQL et renvoie les résultats."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """Exécute une requête SQL sans récupérer de résultats."""
    db = get_db()
    db.execute(query, args)
    db.commit()

# Fonction de validation
def validate_vente(design, prix, quantite):
    """Valide les données d'une vente."""
    errors = []
    
    if not design or not isinstance(design, str) or len(design) > 100:
        errors.append("La désignation doit être une chaîne non vide de maximum 100 caractères.")
    
    try:
        prix_float = float(prix)
        if prix_float <= 0:
            errors.append("Le prix doit être positif.")
    except (ValueError, TypeError):
        errors.append("Le prix doit être un nombre.")
    
    try:
        quantite_int = int(quantite)
        if quantite_int <= 0:
            errors.append("La quantité doit être un entier positif.")
    except (ValueError, TypeError):
        errors.append("La quantité doit être un entier.")
    
    return errors

# Authentification
def token_required(f):
    """Décorateur pour vérifier le token JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token manquant!'}), 401
        
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = query_db('SELECT * FROM users WHERE id = ?', (data['user_id'],), one=True)
        except:
            return jsonify({'message': 'Token invalide!'}), 401
        
        return f(current_user, *args, **kwargs)
    
    return decorated

# Routes pour l'authentification
@app.route('/api/register', methods=['POST'])
@limiter.limit("5 per hour")
def register():
    """Enregistrement d'un utilisateur."""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Données incomplètes!'}), 400
    
    username = data['username']
    password = data['password']
    
    # Validation du nom d'utilisateur
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return jsonify({'message': 'Le nom d\'utilisateur doit contenir entre 3 et 20 caractères alphanumériques ou _'}), 400
    
    # Validation du mot de passe
    if len(password) < 8:
        return jsonify({'message': 'Le mot de passe doit contenir au moins 8 caractères'}), 400
    
    # Vérifier si l'utilisateur existe déjà
    user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
    if user:
        return jsonify({'message': 'Utilisateur déjà existant!'}), 409
    
    # Hasher le mot de passe
    hashed_password = generate_password_hash(password)
    
    # Insérer l'utilisateur
    execute_db('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
              (username, hashed_password, 'user'))
    
    return jsonify({'message': 'Utilisateur créé avec succès!'}), 201

@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    """Connexion d'un utilisateur."""
    auth = request.authorization
    
    if not auth or not auth.username or not auth.password:
        data = request.get_json()
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({'message': 'Authentification requise!'}), 401
        username = data['username']
        password = data['password']
    else:
        username = auth.username
        password = auth.password
    
    user = query_db('SELECT * FROM users WHERE username = ?', (username,), one=True)
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'message': 'Identifiants incorrects!'}), 401
    
    # Générer un token JWT
    token = jwt.encode({
        'user_id': user['id'],
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    
    return jsonify({'token': token})

# Routes pour les ventes
@app.route('/api/ventes', methods=['GET'])
@token_required
def get_all_ventes(current_user):
    """Récupérer toutes les ventes."""
    ventes = query_db('SELECT * FROM ventes')
    
    output = []
    for vente in ventes:
        vente_data = {
            'numProduit': vente['numProduit'],
            'design': vente['design'],
            'prix': vente['prix'],
            'quantite': vente['quantite'],
            'created_at': vente['created_at'],
            'updated_at': vente['updated_at']
        }
        output.append(vente_data)
    
    return jsonify({'ventes': output})

@app.route('/api/ventes/<int:num_produit>', methods=['GET'])
@token_required
def get_one_vente(current_user, num_produit):
    """Récupérer une vente par son numéro."""
    vente = query_db('SELECT * FROM ventes WHERE numProduit = ?', (num_produit,), one=True)
    
    if not vente:
        return jsonify({'message': 'Vente non trouvée!'}), 404
    
    vente_data = {
        'numProduit': vente['numProduit'],
        'design': vente['design'],
        'prix': vente['prix'],
        'quantite': vente['quantite'],
        'created_at': vente['created_at'],
        'updated_at': vente['updated_at']
    }
    
    return jsonify({'vente': vente_data})

@app.route('/api/ventes', methods=['POST'])
@token_required
def create_vente(current_user):
    """Créer une nouvelle vente."""
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'Aucune donnée fournie!'}), 400
    
    design = data.get('design')
    prix = data.get('prix')
    quantite = data.get('quantite')
    
    errors = validate_vente(design, prix, quantite)
    if errors:
        return jsonify({'message': 'Données invalides', 'errors': errors}), 400
    
    # Vérifier si l'article existe déjà
    existing_vente = query_db('SELECT * FROM ventes WHERE design = ?', (design,), one=True)
    if existing_vente:
        return jsonify({'message': 'Un article avec cette désignation existe déjà!'}), 409
    
    execute_db('INSERT INTO ventes (design, prix, quantite) VALUES (?, ?, ?)',
              (design, prix, quantite))
    
    return jsonify({'message': 'Vente créée avec succès!'}), 201

@app.route('/api/ventes/<int:num_produit>', methods=['PUT'])
@token_required
def update_vente(current_user, num_produit):
    """Mettre à jour une vente."""
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'Aucune donnée fournie!'}), 400
    
    vente = query_db('SELECT * FROM ventes WHERE numProduit = ?', (num_produit,), one=True)
    
    if not vente:
        return jsonify({'message': 'Vente non trouvée!'}), 404
    
    design = data.get('design', vente['design'])
    prix = data.get('prix', vente['prix'])
    quantite = data.get('quantite', vente['quantite'])
    
    errors = validate_vente(design, prix, quantite)
    if errors:
        return jsonify({'message': 'Données invalides', 'errors': errors}), 400
    
    execute_db('''
    UPDATE ventes 
    SET design = ?, prix = ?, quantite = ?, updated_at = CURRENT_TIMESTAMP 
    WHERE numProduit = ?
    ''', (design, prix, quantite, num_produit))
    
    return jsonify({'message': 'Vente mise à jour avec succès!'})

@app.route('/api/ventes/<int:num_produit>', methods=['DELETE'])
@token_required
def delete_vente(current_user, num_produit):
    """Supprimer une vente."""
    vente = query_db('SELECT * FROM ventes WHERE numProduit = ?', (num_produit,), one=True)
    
    if not vente:
        return jsonify({'message': 'Vente non trouvée!'}), 404
    
    execute_db('DELETE FROM ventes WHERE numProduit = ?', (num_produit,))
    
    return jsonify({'message': 'Vente supprimée avec succès!'})

# Gestion des erreurs
@app.errorhandler(404)
def not_found(error):
    return jsonify({'message': 'Ressource non trouvée!'}), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'message': 'Méthode non autorisée!'}), 405

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Erreur interne du serveur!'}), 500

# Route de santé
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Utiliser un environnement de production avec waitress ou gunicorn
    # Pour le développement:
    app.run(debug=False, host='0.0.0.0', port=5000)
