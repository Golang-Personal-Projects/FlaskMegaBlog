"""updated the timestamp column of notifications table

Revision ID: 104c5c948b8b
Revises: aa41dd83eb35
Create Date: 2025-02-17 00:45:12.062661

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '104c5c948b8b'
down_revision = 'aa41dd83eb35'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.alter_column('timestamp',
               existing_type=sa.FLOAT(),
               type_=sa.DateTime(),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('notification', schema=None) as batch_op:
        batch_op.alter_column('timestamp',
               existing_type=sa.DateTime(),
               type_=sa.FLOAT(),
               existing_nullable=False)

    # ### end Alembic commands ###
