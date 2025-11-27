import psycopg2
try:
    conn_string = "dbname='test_nk9z' user='mass' password='49BmlMDZsepkqrMGKNFgecuDWeUXdBPE' host='dpg-d4eddshr0fns73blri20-a.oregon-postgres.render.com' port='5432'"
    conn=psycopg2.connect(conn_string)
    cursor=conn.cursor()
except psycopg2.IntegrityError as e:
    print(e)

else:
    print('connexion réusssie')

try:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        is_admin BOOLEAN DEFAULT FALSE
    );
    """)

    conn.commit()
except psycopg2.IntegrityError as e:
    print(e)

else:
    print("Table users créée avec succès !")
    cursor.close()

