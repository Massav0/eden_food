import os
import secrets
from datetime import timedelta
from flask import Flask, session, redirect, url_for, request, jsonify, render_template
import psycopg2

from dotenv import load_dotenv
load_dotenv()  

import datetime
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor=conn.cursor()
except psycopg2.IntegrityError as e:
    print(e)

else:
    print('connexion réusssie')



stats={}
stats['total']=100
stats['achat_annulé']=50

print(stats['total'])
   





