# -*- coding: utf-8 -*-
# Generated by Django 1.9.5 on 2016-04-07 20:23
from __future__ import unicode_literals

from django.db import migrations, models
import featreq.utils


class Migration(migrations.Migration):

    dependencies = [
        ('featreq', '0012_auto_20160407_2021'),
    ]

    operations = [
        migrations.AlterField(
            model_name='closedreq',
            name='closed_at',
            field=models.DateTimeField(blank=True, default=featreq.utils.approxnow, editable=False, verbose_name='Closed at'),
        ),
        migrations.AlterField(
            model_name='openreq',
            name='opened_at',
            field=models.DateTimeField(blank=True, default=featreq.utils.approxnow, editable=False, verbose_name='Opened at'),
        ),
    ]