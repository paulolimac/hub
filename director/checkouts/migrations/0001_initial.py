# Generated by Django 2.0.7 on 2018-07-21 05:13

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Checkout',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='When this event was created')),
                ('status', models.CharField(choices=[('L', 'Launching'), ('O', 'Open'), ('C', 'Closed'), ('F', 'Failed')], help_text='Status of the checkout', max_length=1)),
                ('creator', models.ForeignKey(help_text='User who created the checkout', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checkouts_created', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='CheckoutEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField(auto_now_add=True, help_text='When this event was created')),
                ('type', models.CharField(choices=[('I', 'Info'), ('S', 'Start'), ('F', 'Finish'), ('W', 'Warning'), ('E', 'Error')], help_text='Type of event', max_length=1)),
                ('topic', models.CharField(help_text='Topic of event', max_length=32)),
                ('data', models.TextField(help_text='Data associated with the event, serialised as JSON')),
                ('message', models.TextField(help_text='Event message designed for user consumption')),
                ('checkout', models.ForeignKey(help_text='Checkout that this event relates to', on_delete=django.db.models.deletion.CASCADE, related_name='events', to='checkouts.Checkout')),
            ],
        ),
    ]
