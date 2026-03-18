from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import mysql.connector
import os

# ================================================================
#  APPLICATION
# ================================================================

app = Flask(__name__)
app.secret_key = 'ceg1_epke_secret_2024'

# ================================================================
#  CONFIGURATION
# ================================================================

DB_HOST     = 'localhost'
DB_USER     = 'root'
DB_PASSWORD = ''            # vide par défaut sur XAMPP
DB_NAME     = 'ceg1_epke'

UPLOAD_FOLDER      = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ================================================================
#  UTILITAIRES
# ================================================================

def get_db():
    """Retourne une connexion MySQL."""
    return mysql.connector.connect(
        host     = DB_HOST,
        user     = DB_USER,
        password = DB_PASSWORD,
        database = DB_NAME
    )

def allowed_file(filename):
    """Vérifie si l'extension est autorisée."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, prefix):
    """Sauvegarde un fichier uploadé et retourne son nom, ou None."""
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{prefix}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

# ================================================================
#  ROUTE 1 — Accueil
# ================================================================

@app.route('/')
def index():
    return render_template('index.html')

# ================================================================
#  ROUTE 2 — Inscription élève
# ================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nom            = request.form.get('nom', '').strip()
        prenom         = request.form.get('prenom', '').strip()
        date_naissance = request.form.get('date_naissance', '').strip()
        classe         = request.form.get('classe', '').strip()
        telephone      = request.form.get('telephone', '').strip()
        mot_de_passe   = request.form.get('mot_de_passe', '').strip()

        if not all([nom, prenom, date_naissance, classe, telephone, mot_de_passe]):
            flash('Tous les champs obligatoires doivent être remplis.', 'error')
            return render_template('register.html')

        try:
            conn   = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO candidats
                    (nom, prenom, date_naissance, classe, telephone,
                     mot_de_passe, statut)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (nom, prenom, date_naissance, classe, telephone,
                  mot_de_passe, 'dossier incomplet'))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Inscription réussie ! Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.IntegrityError:
            flash('Ce numéro de téléphone est déjà utilisé.', 'error')
        except Exception as e:
            flash(f"Erreur : {str(e)}", 'error')

    return render_template('register.html')

# ================================================================
#  ROUTE 3 — Connexion élève
# ================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('candidat_id'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        telephone    = request.form.get('telephone', '').strip()
        mot_de_passe = request.form.get('mot_de_passe', '').strip()

        if not telephone or not mot_de_passe:
            flash('Veuillez remplir tous les champs.', 'error')
            return render_template('login.html')

        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT * FROM candidats
                WHERE telephone = %s AND mot_de_passe = %s
            """, (telephone, mot_de_passe))
            candidat = cursor.fetchone()
            cursor.close()
            conn.close()

            if candidat:
                session['candidat_id']  = candidat['id']
                session['candidat_nom'] = candidat['prenom']
                flash(f"Bienvenue, {candidat['prenom']} !", 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Numéro de téléphone ou mot de passe incorrect.', 'error')

        except Exception as e:
            flash(f"Erreur : {str(e)}", 'error')

    return render_template('login.html')

# ================================================================
#  ROUTE 4 — Déconnexion élève
# ================================================================

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

# ================================================================
#  ROUTE 5 — Dashboard élève
# ================================================================

@app.route('/dashboard')
def dashboard():
    if not session.get('candidat_id'):
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM candidats WHERE id = %s", (session['candidat_id'],))
        candidat = cursor.fetchone()
        cursor.close()
        conn.close()

        if not candidat:
            session.clear()
            return redirect(url_for('login'))

        return render_template('dashboard.html', candidat=candidat)

    except Exception as e:
        flash(f"Erreur : {str(e)}", 'error')
        return redirect(url_for('login'))

# ================================================================
#  ROUTE 6 — Upload documents depuis le dashboard
# ================================================================

@app.route('/upload_documents', methods=['POST'])
def upload_documents():
    if not session.get('candidat_id'):
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))

    candidat_id = session['candidat_id']

    # Récupérer les infos actuelles du candidat
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT telephone, acte_naissance, bulletin FROM candidats WHERE id = %s", (candidat_id,))
    candidat = cursor.fetchone()
    cursor.close()
    conn.close()

    telephone     = candidat['telephone']
    acte_file     = request.files.get('acte_naissance')
    bulletin_file = request.files.get('bulletin')

    acte_filename     = save_file(acte_file,     f"acte_{telephone}")
    bulletin_filename = save_file(bulletin_file, f"bulletin_{telephone}")

    # Construire la liste des champs à mettre à jour
    updates = []
    values  = []

    if acte_filename:
        updates.append("acte_naissance = %s")
        values.append(acte_filename)

    if bulletin_filename:
        updates.append("bulletin = %s")
        values.append(bulletin_filename)

    if not updates:
        flash('Aucun fichier valide soumis. Formats acceptes : PDF, JPG, PNG.', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Déterminer l'état final des deux documents après cet upload
        acte_final     = acte_filename     or candidat['acte_naissance']
        bulletin_final = bulletin_filename or candidat['bulletin']

        # Récupérer le statut paiement actuel
        conn2   = get_db()
        cur2    = conn2.cursor(dictionary=True)
        cur2.execute("SELECT paiement FROM candidats WHERE id = %s", (candidat_id,))
        paiement_actuel = cur2.fetchone()['paiement']
        cur2.close()
        conn2.close()

        # Les deux docs présents ET paiement effectué → en attente
        dossier_complet = acte_final and bulletin_final and paiement_actuel == 'payé'

        if dossier_complet:
            updates.append("statut = %s")
            values.append('en attente')

        values.append(candidat_id)
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            f"UPDATE candidats SET {', '.join(updates)} WHERE id = %s",
            tuple(values)
        )
        conn.commit()
        cursor.close()
        conn.close()

        if dossier_complet:
            flash('Dossier complet ! Votre candidature est maintenant en attente de validation.', 'success')
        elif acte_final and bulletin_final and paiement_actuel != 'payé':
            flash('Documents reçus. Il vous reste à effectuer le paiement pour finaliser votre dossier.', 'info')
        else:
            flash('Document(s) soumis. Soumettez le document manquant pour completer votre dossier.', 'info')

    except Exception as e:
        flash(f"Erreur lors de l'upload : {str(e)}", 'error')

    return redirect(url_for('dashboard'))

# ================================================================
#  ROUTE 7 — Paiement (simulation)
# ================================================================

@app.route('/paiement', methods=['GET', 'POST'])
def paiement():
    if not session.get('candidat_id'):
        flash('Veuillez vous connecter.', 'error')
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM candidats WHERE id = %s", (session['candidat_id'],))
    candidat = cursor.fetchone()
    cursor.close()
    conn.close()

    if candidat['paiement'] == 'payé':
        flash('Votre paiement a déjà été effectué.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)

            # Vérifier si les deux documents sont déjà présents
            cursor.execute("SELECT acte_naissance, bulletin FROM candidats WHERE id = %s", (session['candidat_id'],))
            docs = cursor.fetchone()
            dossier_complet = docs['acte_naissance'] and docs['bulletin']

            # Mettre à jour paiement, et statut si dossier complet
            if dossier_complet:
                cursor.execute(
                    "UPDATE candidats SET paiement = 'payé', statut = 'en attente' WHERE id = %s",
                    (session['candidat_id'],)
                )
                flash('Paiement validé ! Votre dossier est complet et en attente de validation.', 'success')
            else:
                cursor.execute(
                    "UPDATE candidats SET paiement = 'payé' WHERE id = %s",
                    (session['candidat_id'],)
                )
                flash('Paiement validé. Soumettez vos documents pour finaliser votre dossier.', 'info')

            conn.commit()
            cursor.close()
            conn.close()
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f"Erreur : {str(e)}", 'error')

    return render_template('paiement.html', candidat=candidat)

# ================================================================
#  ROUTE 8 — Connexion admin
# ================================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if session.get('admin'):
        return redirect(url_for('admin'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            flash('Identifiants incorrects.', 'error')

    return render_template('admin_login.html')

# ================================================================
#  ROUTE 9 — Panneau admin
# ================================================================

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    # Récupération des filtres depuis les paramètres GET
    filtre_statut = request.args.get('statut', '').strip()
    filtre_classe = request.args.get('classe', '').strip()

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Construction de la requête avec filtres dynamiques
        query  = "SELECT * FROM candidats WHERE 1=1"
        params = []

        if filtre_statut:
            query += " AND statut = %s"
            params.append(filtre_statut)

        if filtre_classe:
            query += " AND classe = %s"
            params.append(filtre_classe)

        query += " ORDER BY date_inscription DESC"
        cursor.execute(query, params)
        candidats = cursor.fetchall()

        # Récupérer toutes les classes distinctes pour le select
        cursor.execute("SELECT DISTINCT classe FROM candidats ORDER BY classe")
        classes = [row['classe'] for row in cursor.fetchall()]

        # Totaux pour les stats (toujours sur tous les dossiers)
        cursor.execute("SELECT COUNT(*) as total FROM candidats")
        total = cursor.fetchone()['total']

        cursor.execute("SELECT statut, COUNT(*) as nb FROM candidats GROUP BY statut")
        stats_raw = cursor.fetchall()
        stats = {row['statut']: row['nb'] for row in stats_raw}

        cursor.execute("SELECT COUNT(*) as nb FROM candidats WHERE paiement = 'payé'")
        nb_payes = cursor.fetchone()['nb']

        cursor.close()
        conn.close()

        return render_template('admin.html',
            candidats     = candidats,
            classes       = classes,
            total         = total,
            stats         = stats,
            nb_payes      = nb_payes,
            filtre_statut = filtre_statut,
            filtre_classe = filtre_classe
        )

    except Exception as e:
        flash(f"Erreur : {str(e)}", 'error')
        return render_template('admin.html',
            candidats=[], classes=[], total=0,
            stats={}, nb_payes=0,
            filtre_statut='', filtre_classe=''
        )

# ================================================================
#  ROUTE 10 — Détail dossier (admin)
# ================================================================

@app.route('/admin/dossier/<int:id>')
def admin_dossier(id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM candidats WHERE id = %s", (id,))
        c = cursor.fetchone()
        cursor.close()
        conn.close()
        if not c:
            flash('Dossier introuvable.', 'error')
            return redirect(url_for('admin'))
        return render_template('admin_dossier.html', c=c)
    except Exception as e:
        flash(f"Erreur : {str(e)}", 'error')
        return redirect(url_for('admin'))

# ================================================================
#  ROUTE 11 — Valider un candidat
# ================================================================

@app.route('/valider/<int:id>')
def valider(id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE candidats SET statut = 'accepté' WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Candidature acceptée.', 'success')
    except Exception as e:
        flash(f"Erreur : {str(e)}", 'error')
    return redirect(url_for('admin'))

# ================================================================
#  ROUTE 11 — Refuser un candidat
# ================================================================

@app.route('/refuser/<int:id>')
def refuser(id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE candidats SET statut = 'refusé' WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Candidature refusée.', 'info')
    except Exception as e:
        flash(f"Erreur : {str(e)}", 'error')
    return redirect(url_for('admin'))

# ================================================================
#  ROUTE 11 — Déconnexion admin
# ================================================================

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('index'))

# ================================================================
#  LANCEMENT
# ================================================================

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)