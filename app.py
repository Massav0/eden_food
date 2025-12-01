import os
import secrets
from datetime import timedelta
from flask import Flask, session, redirect, url_for, request, jsonify, render_template
import psycopg2
import random
import string

from dotenv import load_dotenv
load_dotenv()  


from flask_wtf import CSRFProtect

def create_app():
    app = Flask(__name__)

    secret = os.getenv('SECRET_KEY')
    if not secret:
        raise RuntimeError("SECRET_KEY manquante — définir la variable d'environnement SECRET_KEY")
    app.config['SECRET_KEY'] = secret
    # production-friendliness
    app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE','1') == '1'
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG','0') == '1'
    print('SECRET_KEY chargée')

    # optionnel : sécurité cookies (ajuster en prod)
    app.config.update(
        SESSION_COOKIE_NAME="session",
        SESSION_COOKIE_SECURE=False,        # en prod -> True (HTTPS obligatoire)
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(days=1),
    )

    # protection CSRF pour tous les forms (Flask-WTF)
    csrf = CSRFProtect(app)

    return app

app = create_app()





@app.route("/")
def index():
    session.clear()
    if session.get('username'):
        return render_template('index.html')  
    else:
        return render_template('connexion.html')




@app.route("/signup", methods=['POST', 'GET'])
def signup():

    if request.method == 'POST':
        print('informations à inscrire' , request.form)
        nom=request.form.get('name')
        mail=request.form.get('email')
        pwd=request.form.get('password')

        def insert_for_signup(n, m, p):
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))            
            cursor=conn.cursor()
            try:
                cursor.execute("""
            INSERT INTO users (name, email, password, is_admin)
            VALUES (%s, %s, %s, %s)
            """, (n, m, p, True))

                conn.commit()
            except psycopg2.IntegrityError as e:
                conn.rollback()
                print(e)

            else:
                print("opération réussie!")
               
        
        insert_for_signup(nom, mail, pwd)



        return render_template('connexion.html')


    else:    
        return render_template('inscription.html')




@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method=='POST':
        print(request.form)
        mail=request.form.get('email')
        pwd=request.form.get('password')

        def verify_user( m, p):
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor=conn.cursor()
            try:
                cursor.execute("""
            SELECT name, is_admin FROM users WHERE email = %s and password = %s
            """, ( m, p))
                
                rows=cursor.fetchone()
                

                print(rows)
                conn.commit()
            except psycopg2.IntegrityError as e:
                conn.rollback()
                print(e)

            else:
                print("opération réussie!")
            
            if rows != None:
                print( 'utilisateur trouvé')
                row=rows[0]
                row_admin=rows[1]
                session['username']=row
                session['is_admin']=row_admin
                print(session)
                if row_admin == False:
                    return redirect (url_for ('menu'))
                else:
                    return redirect(url_for( 'admin_home'))

            else:
                print( 'utilisateur non trouvé')
                return redirect (url_for ('login'))
            
        
        return verify_user(mail, pwd)


    else:
        return render_template('connexion.html')




@app.route("/follow")
def follow():
    if session.get('username'):
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor=conn.cursor()
        try:
            cursor.execute("""
    SELECT * FROM commande
    WHERE nom_client = %s
    ORDER BY created_at DESC
""", (session.get('username'),))

            conn.commit()
        except psycopg2.IntegrityError as e:
            conn.rollback()
            print
            print(e)

        else:
            print("opération réussie!")

        orders_list=cursor.fetchall()
        orders = []
        for order in orders_list:
                orders.append({
                    'id': order[1],
                    'plat_name': order[2],
                    'client_name': order[4],
                    'quantite': order[7],
                    'price': order[11],
                    'addresse': order[6],
                    'tel': order[5],
                    'date': order[12].strftime(" %d-%m-%Y à %Hh %Mmin %Ss"),
                    'note': order[8],
                    'accompagnement': order[9],
                    'status': order[10],
                    'image_url': order[3],
                })
            

        print(orders)
    
    else:
        return redirect(url_for('login'))

    return render_template('suivi.html', orders=orders)





@app.route('/menu')
def menu():
    if session.get('username'):
        items = []
        try :
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor=conn.cursor()
            cursor.execute('SELECT * FROM plats')
        except psycopg2.IntegrityError as e:
            print(e)
            cursor.close()
            conn.rollback()
        else:
            print('opération réussie')
        
        rows=cursor.fetchall()
        print(rows)
        for row in rows:
            print (row)
            items.append({
                'id': row[0],
                'name':row[1],
                'price': row[2],
                'description': row[3],
                'image_url':row[4],
                'category': row[5],
                'tags': row[6]
            })

        print (items)



        return render_template ('menu.html', items=items)

    else:
        return redirect(url_for('login'))   
    

@app.route('/add_session', methods=['POST'])
def add_to_session():
    item_id= request.form.get('item_id')
    item_name= request.form.get('item_name')
    item_img= request.form.get('item_img')
    item_price= request.form.get('item_price')

    if not item_name and item_img:
        print("Aucun item reçu")
        return redirect(url_for('menu'))
    
    else:
        session['plat_id']=item_id
        session['plat_name']=item_name
        session['plat_img']=item_img
        session['plat_price']=item_price
        print(session)
        return redirect(url_for('orders'))




@app.route("/orders", methods=['POST','GET'])
def orders():
    if session.get('username'):

        if request.method=='POST':

            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor=conn.cursor()


            def generer_reference(longueur=14):
                caracteres = string.ascii_uppercase + string.digits
                return "eden_food_" + ''.join(random.choice(caracteres) for _ in range(longueur))

            def creer_reference_unique(conn, longueur=14):
                while True:
                    ref = generer_reference(longueur)
                    cursor.execute("SELECT 1 FROM commande WHERE plat_id = %s", (ref,))
                    if cursor.fetchone() is None:
                        return ref
            print(creer_reference_unique(conn, longueur=14))

            nom_plat=request.form.get('plat')
            id_plat=creer_reference_unique(conn, longueur=14)
            url_plat=request.form.get('plat_image_url')
            nom_client=request.form.get('nom_client')
            tel_client=request.form.get('tel')
            adress_client=request.form.get('adresse')
            quantite=request.form.get('quantite')
            accompagnement=request.form.get('accompagnement')
            note_plat=request.form.get('note')
            prix_plat=request.form.get('plat_price')


            try:
                cursor.execute("""
                INSERT INTO commande (
                    plat_id,
                    plat_name,
                    plat_image_url,
                    nom_client,
                    tel,
                    adresse,
                    quantite,
                    note,
                    accompagnement,
                    statut,
                    prix
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at;
                """, (
                    id_plat,                                 
                    nom_plat,                     
                    url_plat,      
                    nom_client,                       
                    tel_client,                     
                    adress_client,                 
                    quantite,                                   
                    note_plat,                    
                    accompagnement,                            
                    "En attente de paiement",                        
                    prix_plat                            
                ))

                conn.commit()
                return redirect(url_for('menu'))
            
            except psycopg2.IntegrityError as e:
                print('erreur: ', e)
                conn.rollback()
            else:
                print('insertion réussie')
               

        else:


            return render_template('commande.html')

    else:
        return redirect(url_for('login'))


@app.route("/logout")
def logout():
    session.clear()
    return render_template('connexion.html')


@app.route("/contact")
def contact():
    if session.get('username'):
    
        return render_template('contact.html')
    else:
        return redirect(url_for('login'))


@app.route("/admin_home", methods=['POST', 'GET'])
def admin_home():
    
    if session.get('username') and session.get('is_admin')==True:

        try :
            conn = psycopg2.connect(os.getenv("DATABASE_URL"))
            cursor=conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM commande')
            total = cursor.fetchone()

            cursor.execute('SELECT COUNT(*) FROM commande WHERE statut=%s', ("En attente de paiement",))
            en_attente = cursor.fetchone()

            cursor.execute('SELECT COUNT(*) FROM commande WHERE statut=%s', ("Confirmée",))
            confirme = cursor.fetchone()

            cursor.execute('SELECT COUNT(*) FROM commande WHERE statut=%s', ("En Préparation",))
            en_preparation = cursor.fetchone()

            cursor.execute('SELECT COUNT(*) FROM commande WHERE statut=%s', ("En Livraison",))
            en_livraison = cursor.fetchone()

            cursor.execute('SELECT COUNT(*) FROM commande WHERE statut=%s', ("Livrée",))
            livre = cursor.fetchone()

            cursor.execute('SELECT SUM(prix) FROM commande')
            chiffre = cursor.fetchone()

        except psycopg2.IntegrityError as e:
            print(e)
            cursor.close()
            conn.rollback()
        else:
            print('opération réussie')
        
        
        stats={}
        stats['total']=total[0]
        stats['en_attente']=en_attente[0]
        stats['confirmees']=confirme[0]
        stats['en_preparation']=en_preparation[0]
        stats['en_livraison']=en_livraison[0]
        stats['livrees']=livre[0]
        stats['revenu_total']=chiffre[0]
        print(stats)


        if request.method =='POST':
            try:
                if request.form.get('filter'):
                
                    order_id=request.form.get('status')
                    cursor.execute("""
            SELECT * FROM commande WHERE statut = %s ORDER BY created_at DESC
            """,(order_id,))
                
                elif request.form.get('delete'):
                    order_id=request.form.get('order_id')
                    print(request.form.get('order_id'))
                    print(request.form.get('delete'))
                    cursor.execute("""
                                DELETE FROM commande WHERE plat_id = %s
                            """, (order_id,))
                    
                    conn.commit()

                    cursor.execute("""
            SELECT * FROM commande ORDER BY created_at DESC
            """)


                else:
                    cursor.execute("""
            SELECT * FROM commande ORDER BY created_at DESC
            """)
                
                conn.commit()
            except psycopg2.IntegrityError as e:
                conn.rollback()
                
                print(e)

            else:
                print("opération réussie!")

        else:
            cursor.execute("""
            SELECT * FROM commande ORDER BY created_at DESC
            """)


        orders_list=cursor.fetchall()
        orders = []
        for order in orders_list:
                orders.append({
                    'id': order[1],
                    'plat_name': order[2],
                    'client_name': order[4],
                    'quantite': order[7],
                    'price': order[11],
                    'addresse': order[6],
                    'tel': order[5],
                    'date': order[12].strftime(" %d-%m-%Y à %Hh %Mmin %Ss"),
                    'note': order[8],
                    'accompagnement': order[9],
                    'status': order[10],
                    'image_url': order[3],
                })
        return render_template('admin.html', stats=stats, orders=orders)
    
    else:
        return redirect(url_for('login'))      


        
        



@app.route("/orders_filter", methods=['POST', 'GET'])
def api_filter_orders_status_raw():
    statut = request.args.get('status')
    print(statut)

    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cur = conn.cursor()

    if statut:
        cur.execute("""
            SELECT plat_id, plat_name, created_at, statut, nom_client, prix
            FROM commande
            WHERE statut = %s
            ORDER BY created_at DESC
            LIMIT 20
        """, (statut,))
    else:
        cur.execute("""
            SELECT plat_id, plat_name, created_at, statut, nom_client, prix
            FROM commande
            ORDER BY created_at DESC
            LIMIT 20
        """)

    rows = cur.fetchall()
    # date -> iso string
    for r in rows:
        
        print(r[2])
    cur.close()
    return jsonify(rows)


@app.route("/update_order", methods=['POST','GET'])
def update_order():
    if request.method=='POST':
        order_id=request.form.get('order_id')
        statut=request.form.get('status')
        print(order_id, statut)

        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        cursor=conn.cursor()
        try:
            cursor.execute("""
        UPDATE commande SET statut = %s WHERE plat_id = %s
        """, ( statut, order_id,))
            
            conn.commit()
        except psycopg2.IntegrityError as e:
            conn.rollback()
            print
            print(e)

        else:
            print("opération réussie!")

    else:
        None
    return redirect (url_for('admin_home'))



@app.route("/delete_order", methods=['POST','GET'])
def delete_order():
    return redirect (url_for('admin_home'))


if __name__ == "__main__":
    app.run(debug=True)

