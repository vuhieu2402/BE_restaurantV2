# Generated migration for chatbot metadata

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0003_alter_message_attachment'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='intent',
            field=models.CharField(
                max_length=50,
                blank=True,
                null=True,
                help_text='Detected intent of the message'
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='entities',
            field=models.JSONField(
                blank=True,
                null=True,
                help_text='Extracted entities from the message',
                default=dict,
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='confidence_score',
            field=models.FloatField(
                blank=True,
                null=True,
                help_text='Confidence score of intent classification'
            ),
        ),
        migrations.AddField(
            model_name='message',
            name='is_bot_response',
            field=models.BooleanField(
                default=False,
                help_text='Whether this is a bot response'
            ),
        ),
    ]
