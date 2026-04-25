"""
SEO plugin — models.

`SeoMeta` is a per-object overlay (generic FK) that stores merchant-controlled
title / description / OG image / canonical / robots / structured-data hints.
Models opt in by querying `SeoMeta.for_obj(obj)` from their resolvers; the
plugin makes no assumptions about the host model.

`Redirect` is a small alias map. The plugin's middleware resolves a request
path against this table and 301s if a row exists. `hit_count` and
`last_hit_at` give merchants a sanity check for stale aliases.
"""
from __future__ import annotations

import uuid

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class SeoMeta(models.Model):
    """Per-object SEO override. Generic across any model in the platform."""

    ROBOTS_CHOICES = [
        ('index, follow', 'Index, follow'),
        ('noindex, follow', 'Noindex, follow'),
        ('index, nofollow', 'Index, nofollow'),
        ('noindex, nofollow', 'Noindex, nofollow'),
    ]
    OG_TYPE_CHOICES = [
        ('website', 'Website'),
        ('product', 'Product'),
        ('article', 'Article'),
        ('book', 'Book'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=64)
    target = GenericForeignKey('content_type', 'object_id')

    title = models.CharField(max_length=200, blank=True)
    description = models.CharField(max_length=320, blank=True)
    og_title = models.CharField(max_length=200, blank=True)
    og_description = models.CharField(max_length=320, blank=True)
    og_image = models.URLField(max_length=600, blank=True)
    og_type = models.CharField(max_length=20, choices=OG_TYPE_CHOICES, default='website')
    twitter_card = models.CharField(
        max_length=20, default='summary_large_image',
        help_text='summary | summary_large_image | app | player',
    )
    canonical_url = models.URLField(max_length=600, blank=True)
    robots = models.CharField(max_length=40, choices=ROBOTS_CHOICES, default='index, follow')
    keywords = models.CharField(
        max_length=320, blank=True,
        help_text='Comma-separated. Most engines ignore this; included for completeness.',
    )
    structured_data = models.JSONField(
        default=dict, blank=True,
        help_text='Extra JSON-LD properties merged into the auto-generated payload.',
    )
    auto_filled = models.BooleanField(default=False, help_text='True if filled by AI; False if merchant-edited.')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self) -> str:
        return f'SeoMeta({self.content_type.app_label}.{self.content_type.model}/{self.object_id})'

    @classmethod
    def for_obj(cls, obj) -> 'SeoMeta | None':
        if obj is None:
            return None
        ct = ContentType.objects.get_for_model(type(obj))
        return cls.objects.filter(content_type=ct, object_id=str(obj.pk)).first()


class Redirect(models.Model):
    """301/302 alias from one path to another."""

    KIND_CHOICES = [(301, 'Permanent (301)'), (302, 'Temporary (302)')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_path = models.CharField(max_length=500, unique=True, db_index=True)
    to_path = models.CharField(max_length=500)
    status_code = models.PositiveSmallIntegerField(choices=KIND_CHOICES, default=301)
    is_active = models.BooleanField(default=True, db_index=True)
    note = models.CharField(max_length=200, blank=True)
    hit_count = models.PositiveIntegerField(default=0)
    last_hit_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['from_path']

    def __str__(self) -> str:
        return f'{self.from_path} → {self.to_path}'


class SitemapEntry(models.Model):
    """
    Optional precomputed sitemap entry. Most callers should let the
    sitemap.xml view generate entries on the fly from the catalog;
    this table is for *manual* additions (the homepage, journal posts,
    static pages a merchant wants in the sitemap).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.CharField(max_length=500, unique=True)
    changefreq = models.CharField(
        max_length=10, default='weekly',
        choices=[
            ('always', 'always'), ('hourly', 'hourly'), ('daily', 'daily'),
            ('weekly', 'weekly'), ('monthly', 'monthly'),
            ('yearly', 'yearly'), ('never', 'never'),
        ],
    )
    priority = models.DecimalField(max_digits=3, decimal_places=2, default=0.5)
    last_modified = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
