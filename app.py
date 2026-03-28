from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
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

DB_HOST     = '127.0.0.1'
DB_USER     = 'root'
DB_PASSWORD = ''
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
    return mysql.connector.connect(
        host=DB_HOST, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_file(file, prefix):
    if file and file.filename and allowed_file(file.filename):
        filename = secure_filename(f"{prefix}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

def login_required(f):
    """Décorateur — redirige si l'élève n'est pas connecté."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('candidat_id'):
            flash('Veuillez vous connecter.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Décorateur — redirige si l'admin n'est pas connecté."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

# ================================================================
#  ROUTE 1 — Accueil + recherche numéro de table
# ================================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        numero = request.form.get('numero_table', '').strip().upper()

        if not numero:
            flash('Veuillez entrer un numéro de table.', 'error')
            return render_template('index.html')

        try:
            conn   = get_db()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM laureats WHERE numero_table = %s", (numero,)
            )
            laureat = cursor.fetchone()

            # Vérifier si déjà inscrit
            cursor.execute(
                "SELECT id FROM candidats WHERE numero_table = %s", (numero,)
            )
            deja_inscrit = cursor.fetchone()
            cursor.close()
            conn.close()

            if laureat:
                # Stocker en session pour la page vérification
                session['verification'] = {
                    'numero_table'  : laureat['numero_table'],
                    'nom'           : laureat['nom'],
                    'prenom'        : laureat['prenom'],
                    'date_naissance': str(laureat['date_naissance']),
                    'lieu_naissance': laureat['lieu_naissance'],
                    'sexe'          : laureat['sexe'],
                    'deja_inscrit'  : bool(deja_inscrit)
                }
                return redirect(url_for('verification'))
            else:
                flash(f'Le numéro de table "{numero}" n\'est pas classé au CEG 1 Epkè.', 'error')

        except Exception as e:
            flash(f'Erreur : {str(e)}', 'error')

    return render_template('index.html')

# ================================================================
#  ROUTE 2 — Page de vérification / résultat
# ================================================================

@app.route('/verification')
def verification():
    laureat = session.get('verification')
    if not laureat:
        return redirect(url_for('index'))
    return render_template('verification.html', laureat=laureat)

# ================================================================
#  ROUTE 3 — Inscription (pièces + compte)
# ================================================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    laureat = session.get('verification')
    if not laureat:
        flash('Veuillez d\'abord vérifier votre numéro de table.', 'error')
        return redirect(url_for('index'))

    if laureat.get('deja_inscrit'):
        flash('Ce numéro de table a déjà un compte. Connectez-vous.', 'info')
        return redirect(url_for('login'))

    if request.method == 'POST':
        telephone    = request.form.get('telephone', '').strip()
        mot_de_passe = request.form.get('mot_de_passe', '').strip()

        if not telephone or not mot_de_passe:
            flash('Tous les champs sont obligatoires.', 'error')
            return render_template('register.html', laureat=laureat)

        # ── Validation fichiers — tous obligatoires ──
        acte_file  = request.files.get('acte_naissance')
        cep_file   = request.files.get('certificat_cep')
        photo_file = request.files.get('photo')

        erreurs = []
        if not acte_file or not acte_file.filename:
            erreurs.append("L'acte de naissance est obligatoire.")
        elif not allowed_file(acte_file.filename):
            erreurs.append("L'acte de naissance doit être en PDF, JPG ou PNG.")

        if not cep_file or not cep_file.filename:
            erreurs.append("Le certificat CEP est obligatoire.")
        elif not allowed_file(cep_file.filename):
            erreurs.append("Le certificat CEP doit être en PDF, JPG ou PNG.")

        if not photo_file or not photo_file.filename:
            erreurs.append("La photo d'identité est obligatoire.")
        elif not allowed_file(photo_file.filename):
            erreurs.append("La photo doit être en JPG ou PNG.")

        if erreurs:
            for e in erreurs:
                flash(e, 'error')
            return render_template('register.html', laureat=laureat)

        acte_filename  = save_file(acte_file,  f"acte_{telephone}")
        cep_filename   = save_file(cep_file,   f"cep_{telephone}")
        photo_filename = save_file(photo_file, f"photo_{telephone}")

        try:
            conn   = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO candidats
                    (numero_table, nom, prenom, date_naissance, lieu_naissance,
                     sexe, telephone, mot_de_passe,
                     acte_naissance, certificat_cep, photo,
                     statut)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                laureat['numero_table'],
                laureat['nom'], laureat['prenom'],
                laureat['date_naissance'], laureat['lieu_naissance'],
                laureat['sexe'], telephone, mot_de_passe,
                acte_filename, cep_filename, photo_filename,
                'en attente'
            ))
            conn.commit()
            cursor.close()
            conn.close()

            session.pop('verification', None)
            flash('Dossier soumis avec succès ! Connectez-vous pour suivre votre inscription.', 'success')
            return redirect(url_for('login'))

        except mysql.connector.IntegrityError:
            flash('Ce numéro de téléphone est déjà utilisé.', 'error')
        except Exception as e:
            flash(f'Erreur : {str(e)}', 'error')

    return render_template('register.html', laureat=laureat)

# ================================================================
#  ROUTE 4 — Connexion élève
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
                flash(f'Bienvenue, {candidat["prenom"]} !', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Numéro de téléphone ou mot de passe incorrect.', 'error')

        except Exception as e:
            flash(f'Erreur : {str(e)}', 'error')

    return render_template('login.html')

# ================================================================
#  ROUTE 5 — Déconnexion élève
# ================================================================

@app.route('/logout')
def logout():
    session.clear()
    flash('Vous avez été déconnecté.', 'info')
    return redirect(url_for('index'))

# ================================================================
#  ROUTE 6 — Dashboard élève
# ================================================================

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM candidats WHERE id = %s",
            (session['candidat_id'],)
        )
        candidat = cursor.fetchone()
        cursor.close()
        conn.close()

        if not candidat:
            session.clear()
            return redirect(url_for('login'))

        return render_template('dashboard.html', candidat=candidat)

    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')
        return redirect(url_for('login'))

# ================================================================
#  ROUTE 7 — Paiement (accessible uniquement si accepté)
# ================================================================

@app.route('/paiement', methods=['GET', 'POST'])
@login_required
def paiement():
    conn   = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM candidats WHERE id = %s",
        (session['candidat_id'],)
    )
    candidat = cursor.fetchone()
    cursor.close()
    conn.close()

    # Vérifications d'accès
    if candidat['statut'] != 'accepté':
        flash('Le paiement n\'est disponible qu\'après acceptation de votre dossier.', 'error')
        return redirect(url_for('dashboard'))

    if candidat['paiement'] == 'payé':
        flash('Votre paiement a déjà été effectué.', 'info')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            conn   = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE candidats SET paiement = 'payé' WHERE id = %s",
                (session['candidat_id'],)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Paiement effectué ! L\'administration va valider votre inscription.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Erreur : {str(e)}', 'error')

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
#  ROUTE 9 — Panneau admin (liste + filtres GET)
# ================================================================

@app.route('/admin')
@admin_required
def admin():
    filtre_statut = request.args.get('statut', '').strip()
    filtre_classe = request.args.get('classe', '').strip()

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)

        # Exclure les dossiers incomplets — l'admin ne les voit jamais
        statuts_visibles = ['en attente', 'accepté', 'refusé', 'inscrit']

        query  = "SELECT * FROM candidats WHERE statut IN ({})".format(
            ','.join(['%s'] * len(statuts_visibles))
        )
        params = list(statuts_visibles)

        if filtre_statut and filtre_statut in statuts_visibles:
            query  = "SELECT * FROM candidats WHERE statut = %s"
            params = [filtre_statut]

        if filtre_classe:
            query += " AND classe_attribuee = %s"
            params.append(filtre_classe)

        query += " ORDER BY date_inscription DESC"
        cursor.execute(query, params)
        candidats = cursor.fetchall()

        # Classes attribuées distinctes pour le filtre
        cursor.execute(
            "SELECT DISTINCT classe_attribuee FROM candidats "
            "WHERE classe_attribuee IS NOT NULL ORDER BY classe_attribuee"
        )
        classes = [r['classe_attribuee'] for r in cursor.fetchall()]

        # Stats globales — hors dossiers incomplets
        cursor.execute(
            "SELECT COUNT(*) as total FROM candidats WHERE statut != 'dossier incomplet'"
        )
        total = cursor.fetchone()['total']

        cursor.execute(
            "SELECT statut, COUNT(*) as nb FROM candidats "
            "WHERE statut != 'dossier incomplet' GROUP BY statut"
        )
        stats = {r['statut']: r['nb'] for r in cursor.fetchall()}

        cursor.execute(
            "SELECT COUNT(*) as nb FROM candidats WHERE paiement = 'payé'"
        )
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
        flash(f'Erreur : {str(e)}', 'error')
        return render_template('admin.html',
            candidats=[], classes=[], total=0,
            stats={}, nb_payes=0,
            filtre_statut='', filtre_classe=''
        )

# ================================================================
#  ROUTE 10 — Détail dossier (admin)
# ================================================================

@app.route('/admin/dossier/<int:id>')
@admin_required
def admin_dossier(id):
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
        flash(f'Erreur : {str(e)}', 'error')
        return redirect(url_for('admin'))

# ================================================================
#  ROUTE 10 — Visualiser un document (streaming)
# ================================================================

MIMETYPES = {
    'pdf' : 'application/pdf',
    'jpg' : 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png' : 'image/png',
}

@app.route('/admin/document/<filename>')
@admin_required
def admin_document(filename):
    ext      = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    mimetype = MIMETYPES.get(ext, 'application/octet-stream')
    folder   = os.path.abspath(UPLOAD_FOLDER)
    return send_from_directory(folder, filename, mimetype=mimetype)

# ================================================================
#  ROUTE 11 — Accepter un dossier (statut = en attente requis)
# ================================================================

@app.route('/valider/<int:id>')
@admin_required
def valider(id):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT statut FROM candidats WHERE id = %s", (id,))
        c = cursor.fetchone()

        if not c:
            flash('Dossier introuvable.', 'error')
        elif c['statut'] != 'en attente':
            flash('Ce dossier ne peut pas être accepté (statut invalide).', 'error')
        else:
            cursor.execute(
                "UPDATE candidats SET statut = 'accepté' WHERE id = %s", (id,)
            )
            conn.commit()
            flash('Dossier accepté. L\'élève peut maintenant effectuer son paiement.', 'success')

        cursor.close()
        conn.close()

    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')

    return redirect(url_for('admin_dossier', id=id))

# ================================================================
#  ROUTE 12 — Refuser un dossier (statut = en attente requis)
# ================================================================

@app.route('/refuser/<int:id>')
@admin_required
def refuser(id):
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT statut FROM candidats WHERE id = %s", (id,))
        c = cursor.fetchone()

        if not c:
            flash('Dossier introuvable.', 'error')
        elif c['statut'] != 'en attente':
            flash('Ce dossier ne peut pas être refusé (statut invalide).', 'error')
        else:
            cursor.execute(
                "UPDATE candidats SET statut = 'refusé' WHERE id = %s", (id,)
            )
            conn.commit()
            flash('Dossier refusé.', 'info')

        cursor.close()
        conn.close()

    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')

    return redirect(url_for('admin_dossier', id=id))

# ================================================================
#  ROUTE 13 — Valider paiement + attribuer classe + EDT
# ================================================================

@app.route('/admin/inscrire/<int:id>', methods=['POST'])
@admin_required
def inscrire(id):
    classe_attribuee = request.form.get('classe_attribuee', '').strip()
    emploi_du_temps  = request.form.get('emploi_du_temps', '').strip()

    if not classe_attribuee:
        flash('Veuillez attribuer une classe.', 'error')
        return redirect(url_for('admin_dossier', id=id))

    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT statut, paiement FROM candidats WHERE id = %s", (id,))
        c = cursor.fetchone()

        if not c:
            flash('Dossier introuvable.', 'error')
        elif c['statut'] != 'accepté':
            flash('Le dossier doit être accepté avant de valider l\'inscription.', 'error')
        elif c['paiement'] != 'payé':
            flash('Le paiement n\'a pas encore été effectué par l\'élève.', 'error')
        else:
            cursor.execute("""
                UPDATE candidats
                SET statut = 'inscrit',
                    classe_attribuee = %s,
                    emploi_du_temps  = %s
                WHERE id = %s
            """, (classe_attribuee, emploi_du_temps, id))
            conn.commit()
            flash('Inscription finalisée ! Classe et emploi du temps attribués.', 'success')

        cursor.close()
        conn.close()

    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')

    return redirect(url_for('admin_dossier', id=id))

# ================================================================
#  ROUTE 14 — Gestion des lauréats (liste)
# ================================================================

@app.route('/admin/laureats')
@admin_required
def admin_laureats():
    try:
        conn   = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM laureats ORDER BY numero_table")
        laureats = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('admin_laureats.html', laureats=laureats)
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')
        return render_template('admin_laureats.html', laureats=[])

# ================================================================
#  ROUTE 15 — Ajouter un lauréat
# ================================================================

@app.route('/admin/laureats/ajouter', methods=['POST'])
@admin_required
def ajouter_laureat():
    numero_table   = request.form.get('numero_table', '').strip().upper()
    nom            = request.form.get('nom', '').strip().upper()
    prenom         = request.form.get('prenom', '').strip()
    date_naissance = request.form.get('date_naissance', '').strip()
    lieu_naissance = request.form.get('lieu_naissance', '').strip()
    sexe           = request.form.get('sexe', '').strip()

    if not all([numero_table, nom, prenom]):
        flash('Numéro de table, nom et prénom sont obligatoires.', 'error')
        return redirect(url_for('admin_laureats'))

    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO laureats
                (numero_table, nom, prenom, date_naissance, lieu_naissance, sexe)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (numero_table, nom, prenom,
              date_naissance or None,
              lieu_naissance or None,
              sexe or None))
        conn.commit()
        cursor.close()
        conn.close()
        flash(f'Lauréat {prenom} {nom} ({numero_table}) ajouté.', 'success')

    except mysql.connector.IntegrityError:
        flash(f'Le numéro de table {numero_table} existe déjà.', 'error')
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')

    return redirect(url_for('admin_laureats'))

# ================================================================
#  ROUTE 16 — Supprimer un lauréat
# ================================================================

@app.route('/admin/laureats/supprimer/<int:id>')
@admin_required
def supprimer_laureat(id):
    try:
        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM laureats WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Lauréat supprimé.', 'info')
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'error')
    return redirect(url_for('admin_laureats'))

# ================================================================
#  ROUTE 17 — Déconnexion admin
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
    app.run(debug=True, host='127.0.0.1', port=5000)