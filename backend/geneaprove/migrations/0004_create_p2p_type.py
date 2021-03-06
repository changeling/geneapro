# -*- coding: utf-8 -*-
# Generated by Django 1.10.6 on 2018-03-28 08:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion

def forward(apps, schema_editor):
    P2PT = apps.get_model('geneaprove', 'P2P_Type')
    db_alias = schema_editor.connection.alias

    P2PT.objects.using(db_alias).bulk_create([
        P2PT(id=1, name="same as"),
        P2PT(name="godfather"),
        P2PT(name="godmother"),
    ])


class Migration(migrations.Migration):

    dependencies = [
        ('geneaprove', '0003_initial_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='P2P_Type',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.TextField()),
            ],
            options={
                'db_table': 'p2p_type',
            },
        ),
        migrations.AlterField(
            model_name='p2p',
            name='type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='geneaprove.P2P_Type'),
        ),
        migrations.RunPython(forward),
    ]
