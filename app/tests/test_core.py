#!/usr/bin/env python3
"""Tests rapides de la logique métier de Tcontrol (sans GUI ni réseau).

Lancer :  python tests/test_core.py   (depuis le dossier app/)
"""
import os
import sys
import tempfile
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Redirige le stockage vers un dossier temporaire AVANT d'importer les modules
_tmp = tempfile.mkdtemp(prefix="tcontrol-test-")
os.environ["APPDATA"] = _tmp  # utilisé par config.app_data_dir sous Windows
os.environ["HOME"] = _tmp     # utilisé ailleurs

from core.logic import logical_day, fmt_duration, normalize_process_name, is_valid_process_name
from core.state import State
from core import crypto

FAILED = []

def check(name, cond):
    print(("  ✅" if cond else "  ❌"), name)
    if not cond:
        FAILED.append(name)


print("== logical_day ==")
check("reset 0h → jour calendaire",
      logical_day(0, datetime(2026, 9, 10, 23, 30)) == "2026-09-10")
check("reset 0h à 3h du matin → même jour",
      logical_day(0, datetime(2026, 9, 10, 3, 0)) == "2026-09-10")
check("reset 4h à 2h du matin → encore la veille",
      logical_day(4, datetime(2026, 9, 10, 2, 0)) == "2026-09-09")
check("reset 4h à 18h → jour même",
      logical_day(4, datetime(2026, 9, 10, 18, 0)) == "2026-09-10")

print("== fmt_duration ==")
check("7200 → '2 h 00 min'", fmt_duration(7200) == "2 h 00 min")
check("300 → '5 min'", fmt_duration(300) == "5 min")
check("45 → '45 s'", fmt_duration(45) == "45 s")
check("négatif → 0 s", fmt_duration(-5) == "0 s")

print("== noms de processus ==")
check("Fortnite.EXE → fortnite.exe", normalize_process_name("  Fortnite.EXE ") == "fortnite.exe")
check("valide : 'my game-v2.exe'", is_valid_process_name("my game-v2.exe"))
check("invalide : 'evil?.exe'", not is_valid_process_name("evil?.exe"))
check("invalide : vide", not is_valid_process_name(""))

print("== State : comptage et blocage ==")
st = State()
st.day = logical_day(st.reset_hour)
st.limit = 120                       # 2 minutes pour le test
st.server_used = 60
check("local_used = serveur + pending", abs(st.local_used() - 60) < 0.01)
st.add_play_time(30)
check("pending ajouté", abs(st.local_used() - 90) < 0.01)
check("pas bloqué (90 < 120)", not st.is_blocked())
check("remaining = 30", abs(st.remaining() - 30) < 0.01)
st.add_play_time(40)
check("bloqué (130 >= 120)", st.is_blocked())
check("remaining = 0", st.remaining() == 0)

print("== State : absorption serveur après ping ==")
st2 = State()
st2.day = "2026-09-10"
st2.limit = 7200
st2.add_play_time(120)
resp = {"day": "2026-09-10", "used": 1500, "limit": 3600, "reset_hour": 0,
        "blocked": False, "alias": "Lucas", "processes": ["Steam.exe"]}
changed = st2.on_ping_success(resp)
check("jour inchangé → False", changed is False)
check("server_used appliqué", st2.server_used == 1500)
check("limite appliquée", st2.limit == 3600)
check("delta absorbé", st2.pending_delta == 0)
check("processus normalisés", st2.processes == ["steam.exe"])
check("alias", st2.alias == "Lucas")

resp_new_day = dict(resp, day="2026-09-11", used=0)
check("changement de jour détecté", st2.on_ping_success(resp_new_day) is True)

print("== State : notifications 10/5/0 (une seule fois chacune) ==")
st3 = State()
st3.day = logical_day(st3.reset_hour)
st3.limit = 700
st3.server_used = 0
check("reste 11 min → rien (700 > 600)", st3.check_notification() is None)
st3.server_used = 101  # reste 599 <= 600
check("seuil 600 déclenché", st3.check_notification() == 600)
check("600 pas redéclenché", st3.check_notification() is None)
st3.server_used = 405  # reste 295 <= 300
check("seuil 300 déclenché", st3.check_notification() == 300)
st3.server_used = 700  # reste 0
check("seuil 0 déclenché", st3.check_notification() == 0)
check("0 pas redéclenché", st3.check_notification() is None)

print("== State : nouveau jour ==")
st3.new_day_reset("2026-09-11")
check("compteurs remis à zéro",
      st3.server_used == 0 and st3.pending_delta == 0
      and st3.blocked_server is False and st3.kills_today == 0)
st3.limit = 600
check("notifications réarmées", st3.check_notification() == 600)

print("== State : nouveau jour annoncé par le serveur ==")
st5 = State()
st5.day = "2026-09-10"
st5.limit = 500
st5.server_used = 200       # reste 300
st5.check_notification()    # déclenche le seuil 300
resp_next = {"day": "2026-09-11", "used": 0, "limit": 500, "reset_hour": 0,
             "blocked": False, "alias": "", "processes": []}
check("jour serveur changé", st5.on_ping_success(resp_next) is True)
check("notifications réarmées côté serveur aussi",
      st5.check_notification() == 600)  # reste 500 <= 600 → 10 min re-notifiée

print("== State : persistance ==")
st3.save()
st4 = State.load()
check("jour conservé", st4.day == "2026-09-11")
check("limite conservée", st4.limit == 600)

print("== crypto : déblocage hors ligne ==")
cache = crypto.remember_admin("Admin", "motdepasse42", {})
check("bon mdp accepté", crypto.verify_admin("Admin", "motdepasse42", cache))
check("casse du login ignorée", crypto.verify_admin("ADMIN", "motdepasse42", cache))
check("mauvais mdp refusé", not crypto.verify_admin("Admin", "autre", cache))
check("user inconnu refusé", not crypto.verify_admin("root", "motdepasse42", cache))

print()
if FAILED:
    print(f"❌ {len(FAILED)} test(s) échoué(s) : {FAILED}")
    sys.exit(1)
print("✅ Tous les tests passent.")
