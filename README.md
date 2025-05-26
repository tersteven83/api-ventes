# API de Gestion des Ventes

Cette API REST Flask permet de gérer une table de ventes dans une base de données SQLite, avec possibilité d'utiliser d'autres SGBDR.

## Caractéristiques

- Authentification JWT
- Validation des entrées
- Limitation de débit pour prévenir les attaques par force brute
- Gestion des erreurs
- Bonnes pratiques de sécurité

## Installation

1. Cloner le dépôt
```bash
git clone https://github.com/votre-username/api-ventes.git
cd api-ventes
```

2. Créer un environnement virtuel et installer les dépendances
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Configurer les variables d'environnement
```bash
export SECRET_KEY="votre_clef_secrete_tres_complexe"
export DATABASE="ventes.db"
```

4. Initialiser la base de données
```bash
flask init-db
```

## Dépendances

Créez un fichier `requirements.txt` avec les dépendances suivantes :

```
click==8.2.1
commonmark==0.9.1
Deprecated==1.2.18
Flask==2.1.1
Flask-Cors==3.0.10
Flask-Limiter==2.4.0
itsdangerous==2.2.0
Jinja2==3.1.6
limits==5.2.0
MarkupSafe==3.0.2
packaging==25.0
Pygments==2.19.1
PyJWT==2.3.0
rich==12.6.0
six==1.17.0
typing_extensions==4.13.2
waitress==2.1.1
Werkzeug==2.0.3
wrapt==1.17.2
```

## Démarrage de l'API

### En développement
```bash
flask run
```

### En production
```bash
waitress-serve --host=0.0.0.0 --port=5000 app:app
```

## API Endpoints

### Authentification

#### S'inscrire
```
POST /api/register
```
Payload:
```json
{
    "username": "utilisateur",
    "password": "motdepasse"
}
```

#### Se connecter
```
POST /api/login
```
Payload:
```json
{
    "username": "utilisateur",
    "password": "motdepasse"
}
```
Réponse:
```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Ventes

Tous les endpoints suivants nécessitent un token JWT dans le header :
```
Authorization: Bearer <token>
```

#### Récupérer toutes les ventes
```
GET /api/ventes
```

#### Récupérer une vente spécifique
```
GET /api/ventes/<numProduit>
```

#### Créer une nouvelle vente
```
POST /api/ventes
```
Payload:
```json
{
    "design": "Produit XYZ",
    "prix": 19.99,
    "quantite": 10
}
```

#### Mettre à jour une vente
```
PUT /api/ventes/<numProduit>
```
Payload:
```json
{
    "design": "Produit XYZ modifié",
    "prix": 24.99,
    "quantite": 15
}
```

#### Supprimer une vente
```
DELETE /api/ventes/<numProduit>
```

## Bonnes pratiques de sécurité implémentées

1. **Authentification JWT** : Protection des routes avec tokens JWT
2. **Hachage des mots de passe** : Utilisation de Werkzeug pour un hachage sécurisé
3. **Validation des entrées** : Vérification et nettoyage des données utilisateur
4. **Protection contre les injections SQL** : Utilisation de requêtes paramétrées
5. **Limitation de débit** : Protection contre les attaques par force brute
6. **Gestion des erreurs** : Messages d'erreur appropriés
7. **CORS** : Configuration des Cross-Origin Resource Sharing
8. **Validation des types de données** : Vérification du type et de la plage des valeurs

## Adapter à d'autres SGBDR

Pour utiliser un autre SGBDR comme MySQL ou PostgreSQL:

1. Installez les dépendances nécessaires (par exemple `pip install psycopg2` pour PostgreSQL)
2. Modifiez la fonction `get_db()` pour utiliser le connecteur approprié
3. Ajustez les requêtes SQL si nécessaire

### Exemple avec PostgreSQL

```python
import psycopg2
from psycopg2.extras import DictCursor

def get_db():
    """Connexion à la base de données PostgreSQL."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = psycopg2.connect(
            host="localhost",
            database="ventes",
            user="postgres",
            password="votre_mot_de_passe"
        )
        db.cursor_factory = DictCursor
    return db
```

### Exemple avec MySQL

```python
import mysql.connector
from mysql.connector import Error

def get_db():
    """Connexion à la base de données MySQL."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = mysql.connector.connect(
            host="localhost",
            database="ventes",
            user="root",
            password="votre_mot_de_passe"
        )
    return db
```
