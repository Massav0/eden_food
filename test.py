import os
import secrets
from datetime import timedelta
from flask import Flask, session, redirect, url_for, request, jsonify, render_template
import psycopg2

from dotenv import load_dotenv
load_dotenv()  

import datetime
conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cursor=conn.cursor()


import random
import string
import psycopg2

def generer_reference(longueur=14):
    caracteres = string.ascii_uppercase + string.digits
    return "eden_food_" + ''.join(random.choice(caracteres) for _ in range(longueur))

def creer_reference_unique(conn, longueur=14):
    cur = conn.cursor()
    while True:
        ref = generer_reference(longueur)
        cur.execute("SELECT 1 FROM commande WHERE plat_id = %s", (ref,))
        if cur.fetchone() is None:
            cur.close()
            print(ref)
            return ref
print(creer_reference_unique(conn, longueur=14))





