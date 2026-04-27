import os

from django.conf import settings
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .models import Cat, Foundation, Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)


def _delete_file(field_file):
    if not field_file:
        return
    path = getattr(field_file, 'path', None)
    if path and os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


@receiver(post_delete, sender=Cat)
def cat_photo_post_delete(sender, instance, **kwargs):
    _delete_file(instance.photo)


@receiver(pre_save, sender=Cat)
def cat_photo_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Cat.objects.get(pk=instance.pk)
    except Cat.DoesNotExist:
        return
    if old.photo and old.photo != instance.photo:
        _delete_file(old.photo)


@receiver(post_delete, sender=Foundation)
def foundation_logo_post_delete(sender, instance, **kwargs):
    _delete_file(instance.logo)


@receiver(pre_save, sender=Foundation)
def foundation_logo_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = Foundation.objects.get(pk=instance.pk)
    except Foundation.DoesNotExist:
        return
    if old.logo and old.logo != instance.logo:
        _delete_file(old.logo)
