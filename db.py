# ================================================================
#  CEG 1 Epkè — db.py
#  Connexion MySQL et initialisation de la base de données
#  Ce fichier est importé par app.py
# ================================================================

import mysql.connector
import os

# ================= CONFIGURATION =================

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'ceg1_epke'
}

SECRET_KEY = 'ceg1_epke_secret_2024'

UPLOAD_FOLDER = os.path.join('static', 'uploads')

ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

MAX_FILE_SIZE_MB = 5

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

# ────────────────────────────────────────────────────────────────
#  CONNEXION
# ────────────────────────────────────────────────────────────────

def get_connection():
    """
    Retourne une connexion active à la base de données MySQL.
    À utiliser dans chaque route qui a besoin de la base.

    Usage :
        conn   = get_connection()
        cursor = conn.cursor(dictionary=True)
        ...
        cursor.close()
        conn.close()
    """
    return mysql.connector.connect(**DB_CONFIG)


# ────────────────────────────────────────────────────────────────
#  INITIALISATION
# ────────────────────────────────────────────────────────────────

def init_db():
    """
    Crée la base de données et la table 'candidats' si elles
    n'existent pas encore. Appelée une seule fois au démarrage
    de l'application dans app.py.
    """

    # On se connecte d'abord SANS spécifier la base
    # (elle n'existe peut-être pas encore)
    conn = mysql.connector.connect(
        host     = DB_CONFIG['host'],
        user     = DB_CONFIG['user'],
        password = DB_CONFIG['password']
    )
    cursor = conn.cursor()

    # ── Créer la base si absente ──
    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS ceg1_epke "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute("USE ceg1_epke")

    # ── Créer la table candidats si absente ──
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidats (
            id               INT          AUTO_INCREMENT PRIMARY KEY,
            nom              VARCHAR(100) NOT NULL,
            prenom           VARCHAR(100) NOT NULL,
            date_naissance   DATE         NOT NULL,
            classe           VARCHAR(50)  NOT NULL,
            telephone        VARCHAR(20)  NOT NULL UNIQUE,
            mot_de_passe     VARCHAR(100) NOT NULL,
            acte_naissance   VARCHAR(255) DEFAULT NULL,
            bulletin         VARCHAR(255) DEFAULT NULL,
            statut           VARCHAR(50)  DEFAULT 'en attente',
            paiement         VARCHAR(50)  DEFAULT 'non payé',
            date_inscription TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Base de données 'ceg1_epke' prête.")