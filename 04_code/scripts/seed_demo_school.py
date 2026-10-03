"""Seed de démo : une école crédible, avec 6 semaines d'histoire RÉELLE.

Ce que ce script construit
--------------------------
1 école, 3 classes de CM1 (Grade 4), 75 élèves aux noms plausibles pour le Golfe, et
~6 semaines de réponses datées. Distribution volontairement NON uniforme :

  · Grade 4 — A : cohorte en avance
  · Grade 4 — B : dans la moyenne
  · Grade 4 — C : visiblement en retard, et le retard a une CAUSE nommée
                  (l'équivalence des fractions, en amont de tout le reste)

Trois élèves vitrines sont bloqués sur trois prérequis DIFFÉRENTS, situés sur trois
branches distinctes du graphe — même compétence en échec, causes sans rapport :

  · « Additionner des fractions de dénominateurs différents » bloqué par
    l'équivalence VISUELLE (racine conceptuelle, très en amont) ;
  · … bloqué par les TABLES DE MULTIPLICATION (branche arithmétique : sans elles,
    pas de facteurs, donc pas de PPCM, donc pas de dénominateur commun) ;
  · … bloqué par la FRACTION UNITÉ (racine sur la branche « sens du nombre »).

Pourquoi rejouer le moteur plutôt que d'écrire des Elo
------------------------------------------------------
Les anciens seeds posaient `ability_elo` à la main. Les chiffres étaient donc arbitraires
et le diagnostic ne « trouvait » que ce qu'on y avait mis. Ici chaque réponse passe par
`engine.service.on_response` : Elo, confiance, propagation le long du graphe et diagnostic
causal sont CALCULÉS. Ce qui s'affiche en démo est ce que le produit sait faire, pas une
mise en scène — et si le moteur régresse, la démo le montre.

Usage :
    python scripts/seed_demo_school.py [--students 75] [--weeks 6] [--seed 20260906]

Pré-requis : alembic upgrade head · seed_referentiel · generate_bank_deterministic ·
translate_bank_ar_deterministic · provision de la banque en `active`.
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, select

from src.db import SessionLocal, make_engine
from src.engine.service import on_response
from src.models.base import ItemStatus, Role, utcnow
from src.models.competency import Competency, CompetencyPrerequisite
from src.models.item import Item
from src.models.measurement import Response, School, Student, StudentCompetencyAbility
from src.models.org import (
    AppUser, Classroom, Membership, Organization, ParentStudent, StudentClassroom,
    TeacherClassroom,
)
from src.models.session import AssessmentSession

SCHOOL_NAME = "Al Noor International School"
ORG_NAME = "Al Noor Education Group"
ORG_DOMAIN = "alnoor.demo"

ADMIN_EMAIL = "director@alnoor.demo"
# Les quatre autres personas, pour qu'AUCUN écran du produit ne soit inatteignable en démo
# (revue 2026-09-20 : parent, IT admin et linguiste n'étaient pas semés, et les liens
# magiques partent dans le vide sans SMTP — donc injoignables). Tous passent par
# /demo/login avec le mot de passe partagé.
IT_ADMIN_EMAIL = "it.admin@alnoor.demo"        # console IT (annuaire, sync, audit, export)
PARENT_EMAIL = "parent@alnoor.demo"            # tuteur du 1er élève vitrine (lecture seule)
LINGUIST_EMAIL = "linguist@alnoor.demo"        # staff Atlas global : file de validation AR
TEACHERS = [
    ("teacher.a@alnoor.demo", "Ms. Huda Al Mansoori", "Grade 4 — A"),
    ("teacher.b@alnoor.demo", "Mr. Khalid Al Suwaidi", "Grade 4 — B"),
    ("teacher.c@alnoor.demo", "Ms. Reem Al Hammadi", "Grade 4 — C"),
]

GIVEN = [
    "Ahmed", "Mohammed", "Abdullah", "Khalid", "Saif", "Rashid", "Omar", "Sultan",
    "Hamad", "Faisal", "Majid", "Tariq", "Yousef", "Zayed", "Salem", "Nasser",
    "Hassan", "Ibrahim", "Mansour", "Saeed",
    "Fatima", "Aisha", "Maryam", "Noura", "Latifa", "Shaikha", "Hessa", "Amna",
    "Salama", "Moza", "Reem", "Sara", "Layla", "Huda", "Alia", "Dana",
    "Wadha", "Khawla", "Asma", "Mouza",
]
FAMILY = [
    "Al Mansoori", "Al Suwaidi", "Al Marri", "Al Zaabi", "Al Ketbi", "Al Nuaimi",
    "Al Shamsi", "Al Balushi", "Al Hammadi", "Al Dhaheri", "Al Mazrouei", "Al Falasi",
    "Al Rumaithi", "Al Qubaisi", "Al Kaabi", "Al Hosani", "Al Muhairi", "Al Awadhi",
    "Al Blooshi", "Al Ameri",
]

# Périmètre mesuré : le sous-graphe cohérent d'un niveau Grade 4 (les 32 compétences du
# référentiel ne sont pas toutes de ce niveau — mesurer du Grade 5 ici n'aurait aucun sens).
SCOPE = [
    "MATH.G2.NS.EQUAL_SHARES",
    "MATH.G2.NS.HALVES_QUARTERS",
    "MATH.G2.NS.NAME_FRACTION_VISUAL",
    "MATH.G3.NS.MULT_FACTS",
    "MATH.G3.NF.UNIT_FRACTION",
    "MATH.G3.NF.FRACTION_AS_PART",
    "MATH.G3.NF.EQUIVALENCE_VISUAL",
    "MATH.G3.NF.COMPARE_SAME_DENOM",
    "MATH.G3.NF.ADD_SAME_NOSIMP",
    "MATH.G4.NS.FACTORS",
    "MATH.G4.NS.LCM",
    "MATH.G4.NF.EQUIVALENCE_COMPUTE",
    "MATH.G4.NF.SIMPLIFY_FRACTION",
    "MATH.G4.NF.COMPARE_DIFF_DENOM",
    "MATH.G4.NF.COMMON_DENOM",
    "MATH.G4.NF.ADD_SAME_SIMPLIFY",
    "MATH.G4.NF.ADD_UNLIKE_SIMPLE",
    "MATH.G4.NF.ADD_UNLIKE_LCM",
]

# Profil de classe : (nom, décalage d'aptitude, domaine faible imposé).
# Le décalage déplace l'aptitude latente de TOUS les élèves de la classe ; le domaine
# faible enfonce en plus un sous-arbre précis — c'est lui qui fait « ressortir » la classe
# sur un domaine NOMMÉ, et pas seulement sur une moyenne plus basse.
CLASS_PROFILES = [
    ("Grade 4 — A", +150, None),
    ("Grade 4 — B", 0, None),
    ("Grade 4 — C", -140, "MATH.G3.NF.EQUIVALENCE_VISUAL"),
]

# Sous-arbres de conséquence : ce qu'un blocage sur la racine entraîne en aval.
# (racine, descendants à enfoncer aussi — un élève bloqué en amont échoue en aval)
BLOCKING_ROOTS = {
    "MATH.G3.NF.EQUIVALENCE_VISUAL": [
        "MATH.G4.NF.EQUIVALENCE_COMPUTE", "MATH.G4.NF.SIMPLIFY_FRACTION",
        "MATH.G4.NF.COMPARE_DIFF_DENOM", "MATH.G4.NF.COMMON_DENOM",
        "MATH.G4.NF.ADD_UNLIKE_SIMPLE", "MATH.G4.NF.ADD_UNLIKE_LCM",
        "MATH.G4.NF.ADD_SAME_SIMPLIFY",
    ],
    "MATH.G3.NS.MULT_FACTS": [
        "MATH.G4.NS.FACTORS", "MATH.G4.NS.LCM",
        "MATH.G4.NF.COMMON_DENOM", "MATH.G4.NF.ADD_UNLIKE_LCM",
    ],
    "MATH.G3.NF.UNIT_FRACTION": [
        "MATH.G3.NF.FRACTION_AS_PART", "MATH.G3.NF.ADD_SAME_NOSIMP",
        "MATH.G3.NF.COMPARE_SAME_DENOM", "MATH.G4.NF.ADD_UNLIKE_SIMPLE",
        "MATH.G4.NF.ADD_UNLIKE_LCM",
    ],
}

# Élèves vitrines : (classe, nom, racine bloquante). Trois branches distinctes du graphe.
SHOWCASE = [
    ("Grade 4 — C", "Maryam Al Zaabi", "MATH.G3.NF.EQUIVALENCE_VISUAL"),
    ("Grade 4 — B", "Omar Al Dhaheri", "MATH.G3.NS.MULT_FACTS"),
    ("Grade 4 — C", "Saif Al Kaabi", "MATH.G3.NF.UNIT_FRACTION"),
]

ABILITY_BASE = 1560.0     # aptitude latente médiane d'un élève « dans la moyenne »
ABILITY_SPREAD = 95.0     # écart-type inter-élèves
BLOCKED_ELO = 1210.0      # aptitude latente sur une compétence réellement bloquée
WEAK_DOMAIN_MALUS = -190  # enfoncement supplémentaire du domaine faible d'une classe


def ancestors_of(code: str, hard_prereqs: dict) -> set:
    """Ancêtres HARD transitifs de `code` (protection cycles)."""
    vus, pile = set(), list(hard_prereqs.get(code, []))
    while pile:
        n = pile.pop()
        if n in vus:
            continue
        vus.add(n)
        pile.extend(hard_prereqs.get(n, []))
    return vus


def _p_correct(ability: float, difficulty: float) -> float:
    """Probabilité de réussite (logistique Elo) — même échelle que le moteur."""
    return 1.0 / (1.0 + math.pow(10.0, (difficulty - ability) / 400.0))


def _wipe(s) -> None:
    """Repart d'une école de démo vierge, sans toucher au référentiel ni à la banque.

    Ordre imposé par les clés étrangères : mesures → sessions → rattachements → élèves →
    classes → école → comptes de l'organisation de démo.
    """
    org = s.execute(select(Organization).where(Organization.name == ORG_NAME)).scalar_one_or_none()
    if org is None:
        return
    schools = s.execute(select(School).where(School.organization_id == org.id)).scalars().all()
    school_ids = [sc.id for sc in schools]
    parents_a_purger = set()
    if school_ids:
        student_ids = s.execute(
            select(Student.id).where(Student.school_id.in_(school_ids))
        ).scalars().all()
        # Parents rattachés AD HOC pendant une démo (fiche élève → « ajouter un tuteur ») :
        # leur email n'est pas du domaine de démo, mais leur seule raison d'exister est un
        # élève qu'on efface. Sans ceci, ils survivaient au reset avec un Membership(PARENT)
        # orphelin. Un parent qui a d'autres enfants ou d'autres rôles est conservé.
        if student_ids:
            parent_ids = set(s.execute(
                select(ParentStudent.user_id).where(ParentStudent.student_id.in_(student_ids))
            ).scalars())
            s.execute(delete(ParentStudent).where(ParentStudent.student_id.in_(student_ids)))
            for pid in parent_ids:
                autres_enfants = s.execute(
                    select(ParentStudent).where(ParentStudent.user_id == pid)
                ).first()
                autres_roles = s.execute(
                    select(Membership).where(Membership.user_id == pid,
                                             Membership.role != Role.PARENT)
                ).first()
                if autres_enfants is None and autres_roles is None:
                    parents_a_purger.add(pid)
        if student_ids:
            s.execute(delete(Response).where(Response.student_id.in_(student_ids)))
            s.execute(delete(StudentCompetencyAbility)
                      .where(StudentCompetencyAbility.student_id.in_(student_ids)))
            s.execute(delete(AssessmentSession)
                      .where(AssessmentSession.student_id.in_(student_ids)))
            s.execute(delete(StudentClassroom)
                      .where(StudentClassroom.student_id.in_(student_ids)))
        classroom_ids = s.execute(
            select(Classroom.id).where(Classroom.school_id.in_(school_ids))
        ).scalars().all()
        if classroom_ids:
            s.execute(delete(TeacherClassroom)
                      .where(TeacherClassroom.classroom_id.in_(classroom_ids)))
        s.execute(delete(Student).where(Student.school_id.in_(school_ids)))
        s.execute(delete(Classroom).where(Classroom.school_id.in_(school_ids)))
        s.execute(delete(School).where(School.id.in_(school_ids)))
    users = s.execute(select(AppUser).where(AppUser.email.like(f"%@{ORG_DOMAIN}"))).scalars().all()
    uids = {u.id for u in users} | parents_a_purger
    if uids:
        uids = list(uids)
        s.execute(delete(Membership).where(Membership.user_id.in_(uids)))
        s.execute(delete(TeacherClassroom).where(TeacherClassroom.user_id.in_(uids)))
        s.execute(delete(AppUser).where(AppUser.id.in_(uids)))
    s.execute(delete(Organization).where(Organization.id == org.id))
    s.commit()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--students", type=int, default=75)
    p.add_argument("--weeks", type=int, default=6)
    p.add_argument("--seed", type=int, default=20260906, help="graine — seed reproductible")
    args = p.parse_args()

    rng = random.Random(args.seed)
    now = utcnow()

    with SessionLocal(bind=make_engine()) as s:
        # --- banque : on ne seede rien si rien n'est servable (échec explicite, pas vide) ---
        active_items = s.execute(
            select(Item).where(Item.status == ItemStatus.ACTIVE, Item.deleted_at.is_(None))
        ).scalars().all()
        comps = {c.code: c for c in s.execute(select(Competency)).scalars()}
        scope = [c for c in SCOPE if c in comps]
        items_by_comp = {}
        for it in active_items:
            items_by_comp.setdefault(it.competency_id, []).append(it)
        servable = [c for c in scope if items_by_comp.get(comps[c].id)]
        if len(servable) < len(scope):
            manquantes = sorted(set(scope) - set(servable))
            raise SystemExit(
                "Banque incomplète : aucune question active pour "
                f"{len(manquantes)} compétence(s) du périmètre — {manquantes[:4]}.\n"
                "Lancer d'abord : generate_bank_deterministic.py, "
                "translate_bank_ar_deterministic.py, puis provision_demo.py."
            )

        # Graphe des prérequis HARD, par CODE — sert à protéger les ancêtres des racines
        # vitrines, et à vérifier le résultat en fin de seed.
        code_of = {c.id: c.code for c in comps.values()}
        hard_prereqs = {}
        for e in s.execute(select(CompetencyPrerequisite)).scalars():
            if e.edge_type.value.upper() == "HARD":
                hard_prereqs.setdefault(code_of[e.target_id], []).append(code_of[e.source_id])

        _wipe(s)

        org = Organization(name=ORG_NAME, domain=ORG_DOMAIN)
        s.add(org); s.flush()
        school = School(name=SCHOOL_NAME, organization_id=org.id)
        s.add(school); s.flush()

        director = AppUser(email=ADMIN_EMAIL)
        s.add(director); s.flush()
        s.add(Membership(user_id=director.id, role=Role.PED_ADMIN, school_id=school.id))

        # IT admin : membership porté par l'ORGANISATION (la console IT exige exactement
        # un org_id résolu, cf. _require_it_admin_org) + l'école, pour voir ses classes.
        it_admin = AppUser(email=IT_ADMIN_EMAIL)
        s.add(it_admin); s.flush()
        s.add(Membership(user_id=it_admin.id, role=Role.IT_ADMIN,
                         organization_id=org.id, school_id=school.id))

        # Linguiste : rôle GLOBAL, sans école (la banque n'est pas tenant-scopée).
        linguist = AppUser(email=LINGUIST_EMAIL)
        s.add(linguist); s.flush()
        s.add(Membership(user_id=linguist.id, role=Role.LINGUIST))

        classes = {}
        for email, _name, class_name in TEACHERS:
            cls = Classroom(school_id=school.id, name=class_name)
            s.add(cls); s.flush()
            classes[class_name] = cls
            t = AppUser(email=email)
            s.add(t); s.flush()
            s.add(Membership(user_id=t.id, role=Role.TEACHER, school_id=school.id))
            s.add(TeacherClassroom(user_id=t.id, classroom_id=cls.id))
        s.commit()

        # --- élèves : noms uniques, répartis équitablement sur les 3 classes ---
        noms = set()
        while len(noms) < args.students:
            noms.add(f"{rng.choice(GIVEN)} {rng.choice(FAMILY)}")
        noms = sorted(noms)
        rng.shuffle(noms)

        # Les vitrines occupent une place réservée dans leur classe.
        forced = {nom: (cls_name, root) for cls_name, nom, root in SHOWCASE}
        noms = [n for n in noms if n not in forced][: args.students - len(SHOWCASE)]
        noms.extend(forced)

        per_class = {name: [] for name, _, _ in CLASS_PROFILES}
        libres = [n for n in noms if n not in forced]
        cycle = [name for name, _, _ in CLASS_PROFILES]
        for i, nom in enumerate(libres):
            per_class[cycle[i % len(cycle)]].append(nom)
        for nom, (cls_name, _root) in forced.items():
            per_class[cls_name].append(nom)

        eleves = []   # (Student, aptitudes latentes par code, racine bloquante ou None)
        compteur = 0
        for class_name, offset, weak_domain in CLASS_PROFILES:
            cls = classes[class_name]
            for nom in per_class[class_name]:
                compteur += 1
                u = AppUser(email=f"student{compteur:03d}@{ORG_DOMAIN}")
                s.add(u); s.flush()
                st = Student(school_id=school.id, classroom_id=cls.id, user_id=u.id,
                             display_name=nom, external_ref=f"ALN-{compteur:03d}")
                s.add(st); s.flush()
                s.add(StudentClassroom(student_id=st.id, classroom_id=cls.id))
                s.add(Membership(user_id=u.id, role=Role.STUDENT))

                talent = rng.gauss(0, ABILITY_SPREAD)
                latent = {}
                for code in scope:
                    # Aptitude latente = base + niveau de classe + talent individuel
                    # + difficulté propre de la compétence + bruit par compétence.
                    ecart = (comps[code].difficulty_prior or 1500.0) - 1500.0
                    latent[code] = (ABILITY_BASE + offset + talent
                                    - 0.45 * ecart + rng.gauss(0, 45))

                # Domaine faible de la classe : enfonce la racine ET son aval.
                if weak_domain:
                    for code in [weak_domain] + BLOCKING_ROOTS.get(weak_domain, []):
                        if code in latent:
                            latent[code] += WEAK_DOMAIN_MALUS + rng.gauss(0, 30)

                # Élève vitrine : blocage franc et net sur SA racine, et sur son aval.
                racine = forced.get(nom, (None, None))[1]
                if racine:
                    latent[racine] = BLOCKED_ELO + rng.gauss(0, 20)
                    for aval in BLOCKING_ROOTS[racine]:
                        if aval in latent:
                            latent[aval] = min(latent[aval], BLOCKED_ELO + 60 + rng.gauss(0, 25))
                    # …et bonne maîtrise ailleurs, pour que la cause racine soit LISIBLE
                    # (un élève faible partout ne démontre rien).
                    touche = {racine, *BLOCKING_ROOTS[racine]}
                    for code in scope:
                        if code not in touche:
                            latent[code] = max(latent[code], 1620 + rng.gauss(0, 30))
                    # Les ANCÊTRES de la racine sont hissés plus haut encore. Le diagnostic
                    # remonte au nœud non maîtrisé le plus en amont : si un ancêtre passait
                    # sous le seuil — par bruit ou par propagation depuis l'aval en échec —
                    # c'est LUI qui serait désigné, et la vitrine montrerait une autre cause
                    # que celle annoncée (constaté : la racine de Saif remontait d'un cran).
                    for anc in ancestors_of(racine, hard_prereqs):
                        if anc in latent:
                            latent[anc] = max(latent[anc], 1760 + rng.gauss(0, 20))

                eleves.append((st, latent, racine))
        s.commit()
        print(f"{len(eleves)} élèves créés sur {len(CLASS_PROFILES)} classes.")

        # Parent de démo : rattaché au 1er élève vitrine, source "staff" (jamais
        # auto-déclaré). Lecture seule : trajectoire de l'enfant, aucune session.
        vitrine = next((st for st, _l, racine in eleves if racine), None)
        if vitrine is not None:
            parent = AppUser(email=PARENT_EMAIL)
            s.add(parent); s.flush()
            s.add(Membership(user_id=parent.id, role=Role.PARENT, organization_id=org.id))
            s.add(ParentStudent(user_id=parent.id, student_id=vitrine.id, source="staff"))
            s.commit()

        # --- 6 semaines de réponses, rejouées à travers le MOTEUR ---
        total = 0
        for st, latent, racine in eleves:
            for semaine in range(args.weeks):
                # Une séance par semaine ; la dernière tombe dans la fenêtre du digest (7 j).
                jours = (args.weeks - semaine) * 7 - rng.randint(1, 4)
                quand = now - timedelta(days=max(jours, 1),
                                        hours=rng.randint(8, 14), minutes=rng.randint(0, 59))
                # 4 compétences travaillées par séance : sur 6 semaines, chaque compétence
                # du périmètre reçoit plusieurs mesures DIRECTES (n_direct > 0), condition
                # sine qua non pour qu'elle puisse être désignée cause racine.
                cibles = rng.sample(scope, k=min(8, len(scope)))
                if racine:
                    # La racine est toujours mesurée ; ses ANCÊTRES ne le sont jamais.
                    #
                    # Ce n'est pas un artifice, c'est ce que fait le moteur : une évaluation
                    # de niveau Grade 4 ne re-teste pas le partage en parts égales de Grade 2
                    # chez chaque élève. Et le diagnostic en tient compte — il ne désigne
                    # comme cause racine qu'un nœud RÉELLEMENT estimé, jamais un ancêtre sur
                    # lequel il n'existe aucune observation (diagnosis.py).
                    #
                    # Sans cette règle, le diagnostic remontait au-dessus de la racine
                    # annoncée. Motif mesuré : contre des items faciles — et les compétences
                    # fondamentales le sont — une bonne réponse ne fait presque pas monter
                    # l'Elo (l'écart attendu vaut déjà ~1). Un ancêtre reste donc collé à
                    # 1500 quel que soit le nombre de mesures, et bascule sous le seuil au
                    # moindre effet de propagation depuis l'aval en échec.
                    interdits = ancestors_of(racine, hard_prereqs)
                    cibles = [racine] + [c for c in cibles
                                         if c not in interdits and c != racine][:7]
                for code in cibles:
                    pool = items_by_comp[comps[code].id]
                    for it in rng.sample(pool, k=min(3, len(pool))):
                        juste = rng.random() < _p_correct(latent[code], it.difficulty_elo or 1500.0)
                        resp = on_response(
                            s, student_id=st.id, item_id=it.id, is_correct=juste,
                            school_id=school.id,
                            response_time_ms=rng.randint(6000, 42000),
                        )
                        # Le moteur horodate à `now` : on redate la réponse pour obtenir un
                        # historique (digest 7 jours, lacunes émergentes, progression).
                        resp.created_at = quand
                        total += 1
            s.commit()

        # Les abilities portent la date de la dernière mesure — alignée sur l'historique.
        derniere = s.execute(
            select(Response.student_id, Response.competency_id, Response.created_at)
        ).all()
        vue = {}
        for sid, cid, quand in derniere:
            cle = (sid, cid)
            if cle not in vue or quand > vue[cle]:
                vue[cle] = quand
        for ab in s.execute(select(StudentCompetencyAbility)).scalars():
            quand = vue.get((ab.student_id, ab.competency_id))
            if quand:
                ab.last_measured_at = quand
        s.commit()

        _rapport(s, school, classes, eleves, comps, total, args)


def _rapport(s, school, classes, eleves, comps, total, args) -> None:
    """Vérifie que le seed a produit ce qu'il promet — et l'imprime."""
    from src.restitution.diagnosis import MASTERY_ELO, diagnose

    hard = {}
    code_of = {c.id: c.code for c in comps.values()}
    for e in s.execute(select(CompetencyPrerequisite)).scalars():
        if e.edge_type.value.upper() == "HARD":
            hard.setdefault(code_of[e.target_id], []).append(code_of[e.source_id])

    print(f"\n{total} réponses rejouées à travers le moteur sur {args.weeks} semaines.")
    print("=" * 66)
    print(f"ÉCOLE  {school.name}   (school_id={school.id})")
    print("=" * 66)

    for class_name, cls in classes.items():
        ids = [st.id for st, _, _ in eleves if st.classroom_id == cls.id]
        rows = [a for a in s.execute(
            select(StudentCompetencyAbility)
            .where(StudentCompetencyAbility.student_id.in_(ids))
        ).scalars() if a.n_direct > 0]
        moy = sum(a.ability_elo for a in rows) / len(rows) if rows else 0
        taux = sum(1 for a in rows if a.ability_elo >= MASTERY_ELO) / len(rows) if rows else 0
        # Domaine le plus faible de la classe (celui qui doit « ressortir »).
        par_comp = {}
        for a in rows:
            par_comp.setdefault(code_of[a.competency_id], []).append(a.ability_elo)
        faible = min(par_comp.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))
        print(f"\n  {class_name:14s} {len(ids):3d} élèves · Elo moyen {moy:7.1f} · "
              f"maîtrise {taux*100:4.1f}%")
        print(f"       domaine le plus faible : {faible[0]} "
              f"({sum(faible[1])/len(faible[1]):.0f})")
        print(f"       classroom_id={cls.id}")

    print("\n  Élèves vitrines — trois prérequis bloquants, trois branches :")
    vitrines = []
    for st, _latent, racine in eleves:
        if not racine:
            continue
        vitrines.append(st)
        abilities = {code_of[a.competency_id]: a.ability_elo for a in s.execute(
            select(StudentCompetencyAbility)
            .where(StudentCompetencyAbility.student_id == st.id)
        ).scalars() if a.n_direct > 0}
        d = diagnose("MATH.G4.NF.ADD_UNLIKE_LCM", abilities, hard)
        trouve = d.root_cause if d else "—"
        marque = "OK " if trouve == racine else "!! "
        print(f"    {marque}{st.display_name:24s} attendu {racine}")
        print(f"        diagnostiqué : {trouve}   chaîne : {' → '.join(reversed(d.chain)) if d else '—'}")
        print(f"        student_id={st.id}")

    # Fiche des comptes : c'est CE bloc qu'on garde sous les yeux pendant la démo.
    from src.models.org import AppUser as _AppUser
    email_of = {u.id: u.email for u in s.execute(select(_AppUser)).scalars()}
    eleve_demo = vitrines[0] if vitrines else None
    print("\n" + "=" * 66)
    print("COMPTES DE DÉMO — mot de passe commun : $DEMO_LOGIN_PASSWORD")
    print("=" * 66)
    print(f"  1. Directeur académique  {ADMIN_EMAIL}")
    for email, nom, classe in TEACHERS:
        marque = "  ← classe en difficulté" if classe.endswith("C") else ""
        print(f"  ·  Enseignant {classe:14s} {email}{marque}")
    if eleve_demo is not None:
        print(f"  5. Élève (session live)  {email_of.get(eleve_demo.user_id, '?')}"
              f"   [{eleve_demo.display_name}]")
        print(f"  6. Parent (lecture seule) {PARENT_EMAIL}   [tuteur de {eleve_demo.display_name}]")
    print(f"  7. IT admin (console IT)  {IT_ADMIN_EMAIL}")
    print(f"  8. Linguiste (file AR)    {LINGUIST_EMAIL}")
    print("\n  Les 75 élèves : student001..student%03d@%s" % (len(eleves), ORG_DOMAIN))


if __name__ == "__main__":
    main()
