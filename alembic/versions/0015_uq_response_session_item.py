"""uq_response_session_item — anti double-submit atomique (revue concurrence 2026-07-07)

L'API rejetait le double-submit par une garde applicative NON atomique
(_seen_item_ids) : deux requêtes simultanées passaient la garde toutes les deux et
la réponse était appliquée deux fois. Combinée au response_id déterministe
(uuid5(session_id, item_id)), cette contrainte unique rend le rejet ATOMIQUE :
au plus UNE réponse par (session_id, item_id), le doublon échoue au flush
(IntegrityError → 409 côté API). Les réponses hors session (session_id NULL —
seeds, moteur appelé directement) restent libres : les NULL multiples sont
autorisés par l'unicité SQL (Postgres comme SQLite).

DÉDOUBLONNAGE PRÉALABLE (revue adversariale 2026-07-07) : toute base ayant tourné
avec l'ancienne garde peut déjà contenir des doublons (session_id, item_id) —
exactement les lignes que ce correctif vise. Sans purge, ADD CONSTRAINT échoue et
bloque le déploiement du correctif lui-même. On supprime donc d'abord les doublons
en GARDANT la plus ancienne réponse (created_at puis id, déterministe) par couple
(session_id, item_id) non NULL.

NB : l'ID de révision est volontairement court (≤ 32 caractères) — la colonne
alembic_version.version_num est un VARCHAR(32) par défaut sur Postgres ; un ID
plus long fait échouer `alembic upgrade head` (StringDataRightTruncation).

Revision ID: 0015_uq_response_session_item
Revises: 0014_consumed_token
Create Date: 2026-07-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015_uq_response_session_item"
down_revision: Union[str, None] = "0014_consumed_token"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Purge des doublons hérités de la garde non atomique : on garde la réponse
    #    la plus ANCIENNE par (session_id, item_id). ROW_NUMBER est portable
    #    (Postgres, SQLite ≥ 3.25) ; les session_id NULL ne sont pas concernés.
    op.execute(sa.text(
        """
        DELETE FROM response
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY session_id, item_id
                           ORDER BY created_at, id
                       ) AS rn
                FROM response
                WHERE session_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
        """
    ))
    # 2) batch_alter_table : portable SQLite (recréation de table) + Postgres (ALTER natif).
    with op.batch_alter_table("response") as batch_op:
        batch_op.create_unique_constraint(
            "uq_response_session_item", ["session_id", "item_id"]
        )


def downgrade() -> None:
    # Les doublons purgés ne sont pas restaurables (données invalides par définition) ;
    # on retire seulement la contrainte.
    with op.batch_alter_table("response") as batch_op:
        batch_op.drop_constraint("uq_response_session_item", type_="unique")
