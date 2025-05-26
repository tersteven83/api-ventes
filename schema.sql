-- Schema for the sales database

-- Table des utilisateurs
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

-- Table des ventes
CREATE TABLE IF NOT EXISTS ventes (
    numProduit INTEGER PRIMARY KEY AUTOINCREMENT,
    design TEXT NOT NULL,
    prix REAL NOT NULL,
    quantite INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Créer un utilisateur administrateur par défaut (avec mot de passe à changer)
INSERT OR IGNORE INTO users (username, password, role) 
VALUES ('admin', 'pbkdf2:sha256:150000$xxxxxxxx$yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy', 'admin');