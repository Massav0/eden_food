import psycopg2

conn_string = "postgresql://postgres:Louismassavo91%23@db.ijnzozsridabuqxxfxcz.supabase.co:5432/postgres"

try:
    # Connexion à la base
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()
    print("Connexion réussie !")

    # Création de la table
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
    print("Table 'users' créée avec succès !")

except psycopg2.Error as e:
    print("Erreur PostgreSQL :", e)

finally:
    # Toujours fermer le cursor et la connexion
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close()