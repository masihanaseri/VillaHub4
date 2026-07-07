# Fix: add unique_together constraint to Membership model

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_permission_options_alter_role_options_and_more'),
        ('townships', '0004_alter_townshipsetting_table'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='membership',
            unique_together={('user', 'township', 'role')},
        ),
    ]
