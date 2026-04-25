# db.py — base de données SQLite patients MedFlow AI

import sqlite3
import hashlib
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "patients.db")


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS patients (
        id TEXT PRIMARY KEY,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS consultations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id TEXT NOT NULL,
        date_consult TEXT NOT NULL,
        age INTEGER,
        sexe TEXT,
        poids REAL,
        creatinine REAL,
        dfg REAL,
        stade TEXT,
        na_val REAL,
        k_val REAL,
        phase TEXT,
        c0 REAL,
        dose_actuelle REAL,
        dose_recommandee REAL,
        dose_pk REAL,
        plafond REAL,
        facteur_dfg REAL,
        c0_statut TEXT,
        na_statut TEXT,
        k_statut TEXT,
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )""")
    con.commit()
    con.close()


def generate_patient_id(nom: str, prenom: str) -> str:
    key = f"{prenom.strip().lower()}{nom.strip().lower()}"
    return hashlib.sha256(key.encode()).hexdigest()[:8].upper()


def upsert_patient(pid: str, nom: str, prenom: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO patients (id, nom, prenom, created_at) VALUES (?,?,?,?)",
        (pid, nom.strip().upper(), prenom.strip().capitalize(), datetime.now().isoformat())
    )
    con.commit()
    con.close()


def save_consultation(pid, age, sexe, poids, creat, dfg, stade, na, k, phase,
                      c0, dose_act, dose_rec, dose_pk, plafond, fr,
                      c0_statut, na_statut, k_statut):
    con = sqlite3.connect(DB_PATH)
    con.execute("""INSERT INTO consultations
        (patient_id, date_consult, age, sexe, poids, creatinine, dfg, stade,
         na_val, k_val, phase, c0, dose_actuelle, dose_recommandee, dose_pk,
         plafond, facteur_dfg, c0_statut, na_statut, k_statut)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (pid, datetime.now().strftime("%Y-%m-%d %H:%M"),
         age, sexe, poids, creat, dfg, stade, na, k, phase,
         c0, dose_act, dose_rec, dose_pk, plafond, fr,
         c0_statut, na_statut, k_statut))
    con.commit()
    con.close()


def get_consultations(pid: str) -> list:
    con = sqlite3.connect(DB_PATH)
    cur = con.execute("""SELECT date_consult, age, sexe, poids, creatinine,
        dfg, stade, na_val, k_val, phase, c0, dose_actuelle, dose_recommandee,
        dose_pk, plafond, facteur_dfg, c0_statut, na_statut, k_statut
        FROM consultations WHERE patient_id=? ORDER BY date_consult""", (pid,))
    rows = cur.fetchall()
    con.close()
    return rows


def count_consultations(pid: str) -> int:
    con = sqlite3.connect(DB_PATH)
    n = con.execute("SELECT COUNT(*) FROM consultations WHERE patient_id=?", (pid,)).fetchone()[0]
    con.close()
    return n


def get_all_patients() -> list:
    """Retourne tous les patients avec leur nombre de consultations."""
    con = sqlite3.connect(DB_PATH)
    cur = con.execute("""
        SELECT p.id, p.nom, p.prenom, p.created_at, COUNT(c.id) as nb
        FROM patients p
        LEFT JOIN consultations c ON p.id = c.patient_id
        GROUP BY p.id
        ORDER BY p.nom, p.prenom
    """)
    rows = cur.fetchall()
    con.close()
    return rows


def search_patients(query: str) -> list:
    """Recherche patients par nom ou prénom (insensible à la casse)."""
    con = sqlite3.connect(DB_PATH)
    q = f"%{query.strip().upper()}%"
    cur = con.execute("""
        SELECT p.id, p.nom, p.prenom, p.created_at, COUNT(c.id) as nb
        FROM patients p
        LEFT JOIN consultations c ON p.id = c.patient_id
        WHERE p.nom LIKE ? OR p.prenom LIKE ?
        GROUP BY p.id
        ORDER BY p.nom, p.prenom
    """, (q, q))
    rows = cur.fetchall()
    con.close()
    return rows
