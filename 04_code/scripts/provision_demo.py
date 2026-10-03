"""Provisionne un établissement de démo + ACTIVE la banque — prêt pour un test pilote.

Crée organisation → école → classe → 12 élèves + comptes admin pédagogique / enseignant /
élèves, et fait passer les items de la banque à `active` via le workflow légitime
(approve → validate AR → promote). Idempotent : relancer ne recrée pas les comptes.

Auth = SSO uniquement (plus de mot de passe). Pour tester la démo SANS IdP externe, on
ouvre une session via le simulateur SSO de dev : poser `OIDC_DEV_LOGIN=1` (et `ATLAS_ENV`
non-prod), puis `POST /dev/login {"email": "..."}`. En prod, ces comptes se connectent
via l'IdP de l'établissement (leur email doit exister côté annuaire/rostering).

Usage : DATABASE_URL=... python scripts/provision_demo.py
Pré-requis : alembic upgrade head + banque seedée + traduite AR (translate_bank_ar.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from src.db import SessionLocal, make_engine
from src.items.review import approve, promote_to_active, validate_arabic
from src.models.base import ItemStatus, Role
from src.models.item import Item
from src.models.measurement import School, Student
from src.models.org import (
    AppUser, Classroom, Membership, Organization, StudentClassroom, TeacherClassroom,
)

ADMIN_EMAIL, TEACHER_EMAIL = "admin@demo.atlas", "prof@demo.atlas"
N_STUDENTS = 12


def _provision_tenant(s):
    existing = s.execute(select(AppUser).where(AppUser.email == ADMIN_EMAIL)).scalar_one_or_none()
    if existing:
        teacher = s.execute(select(AppUser).where(AppUser.email == TEACHER_EMAIL)).scalar_one()
        cls = s.execute(select(Classroom)).scalars().first()
        students = s.execute(select(Student)).scalars().all()
        return existing, teacher, cls, students, False

    org = Organization(name="Demo Org"); s.add(org); s.flush()
    school = School(name="Demo School", organization_id=org.id); s.add(school); s.flush()
    cls = Classroom(school_id=school.id, name="Grade 4 — A"); s.add(cls); s.flush()

    # Comptes sans mot de passe : l'auth est portée par l'IdP (SSO). En dev, le simulateur
    # SSO (/dev/login) ouvre une session sur l'email seul.
    admin = AppUser(email=ADMIN_EMAIL)
    teacher = AppUser(email=TEACHER_EMAIL)
    s.add_all([admin, teacher]); s.flush()
    s.add_all([
        Membership(user_id=admin.id, role=Role.PED_ADMIN, school_id=school.id),
        Membership(user_id=teacher.id, role=Role.TEACHER, school_id=school.id),
        TeacherClassroom(user_id=teacher.id, classroom_id=cls.id),
    ])

    students = []
    for i in range(N_STUDENTS):
        u = AppUser(email=f"eleve{i+1}@demo.atlas")
        s.add(u); s.flush()
        st = Student(school_id=school.id, classroom_id=cls.id, user_id=u.id, external_ref=f"S{i+1}")
        s.add(st); s.flush()
        s.add(StudentClassroom(student_id=st.id, classroom_id=cls.id))  # inscription M:N
        s.add(Membership(user_id=u.id, role=Role.STUDENT))
        students.append(st)
    s.commit()
    return admin, teacher, cls, students, True


def _activate_bank(s):
    """Active la banque SANS humain — chemin de DÉMO/CI uniquement.

    En production la chaîne approve → validate_arabic → promote_to_active est portée par
    des comptes identifiés (scripts/review_items.py). Ici, un pseudo-reviewer
    « demo-provision » — refusé en prod, et chaque activation laisse une entrée d'audit
    marquée `automated` pour qu'on ne confonde jamais cette banque avec une banque revue.
    """
    import os
    from src.audit import log_action
    if os.environ.get("ATLAS_ENV", "dev").lower() in ("prod", "production"):
        raise SystemExit("Activation automatique refusée en production : "
                         "utiliser scripts/review_items.py activate --reviewer <email>.")
    items = s.execute(select(Item).where(Item.deleted_at.is_(None))).scalars().all()
    activated = skipped_active = skipped_no_ar = skipped_quarantined = 0
    for it in items:
        if it.status == ItemStatus.ACTIVE:
            skipped_active += 1
            continue
        if it.status == ItemStatus.QUARANTINED:
            skipped_quarantined += 1
            continue
        if not it.content_ar:
            skipped_no_ar += 1
            continue
        approve(s, it, reviewer="demo-provision")
        validate_arabic(s, it, linguist="demo-provision")
        promote_to_active(s, it, reviewer="demo-provision")
        log_action(s, action="item.activate", resource_type="item", resource_id=it.id,
                   details={"actor": "demo-provision", "automated": True})
        activated += 1
    s.commit()
    return activated, skipped_active, skipped_no_ar, skipped_quarantined


def main():
    import argparse
    p = argparse.ArgumentParser()
    # La démo commerciale a sa PROPRE école (seed_demo_school.py). Elle n'a besoin ici que
    # de l'activation de la banque : créer en plus « Demo School » et ses 12 élèves
    # laisserait un établissement fantôme dans la base montrée à un directeur.
    p.add_argument("--bank-only", action="store_true",
                   help="active la banque sans créer le tenant de démo")
    args = p.parse_args()

    engine = make_engine()
    with SessionLocal(bind=engine) as s:
        if args.bank_only:
            activated, already, no_ar, quarantined = _activate_bank(s)
            print(f"Banque : {activated} items activés, {already} déjà actifs, "
                  f"{no_ar} sans AR (ignorés), {quarantined} quarantinés (ignorés)")
            return
        admin, teacher, cls, students, created = _provision_tenant(s)
        activated, already, no_ar, quarantined = _activate_bank(s)

    print("=" * 60)
    print("DÉMO PROVISIONNÉE" if created else "DÉMO DÉJÀ EN PLACE (comptes réutilisés)")
    print("=" * 60)
    print(
        f"Banque : {activated} items activés, {already} déjà actifs, "
        f"{no_ar} sans AR (ignorés), {quarantined} quarantinés (ignorés)"
    )
    print(f"\nClasse : {cls.name}  (id={cls.id})")
    print(f"Élèves : {len(students)}  (ex. student_id={students[0].id if students else 'N/A'})")
    print("\nComptes (auth via SSO — pas de mot de passe) :")
    print(f"  Admin pédagogique : {ADMIN_EMAIL}")
    print(f"  Enseignant        : {TEACHER_EMAIL}")
    print(f"  Élèves            : eleve1..{N_STUDENTS}@demo.atlas")
    print("\n🔑 Tester sans IdP (DEV) : export OIDC_DEV_LOGIN=1  (ATLAS_ENV non-prod)")
    print(f"   curl -XPOST .../dev/login -d '{{\"email\":\"{ADMIN_EMAIL}\"}}' → renvoie un token Bearer")
    print("   En prod : ces emails doivent exister dans l'IdP/annuaire de l'établissement.")


if __name__ == "__main__":
    main()
