from enum import Enum

from django.contrib import admin
from django.db import models
from django.utils.translation import gettext_lazy as _

from choicefield import ChoiceField


class TextChoice(models.TextChoices):
    FIRST = "FIRST", _("first")
    SECOND = "SECOND", _("second")


class IntChoice(models.IntegerChoices):
    ONE = 1, _("one")
    TWO = 2, _("two")


class ChoiceModel(models.Model):
    text_choice = ChoiceField(TextChoice)
    int_choice = ChoiceField(IntChoice)

    class Meta:
        app_label = "test_app"


@admin.register(ChoiceModel)
class ChoiceModelAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    ...


class NullableModel(models.Model):
    choice = ChoiceField(IntChoice, null=True, blank=True)

    class Meta:
        app_label = "test_app"


@admin.register(NullableModel)
class NullableModelAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    ...


class IntegerEnum(int, Enum):
    THREE = 3
    FOUR = 4


class StringEnum(str, Enum):
    A = "A"
    B = "B"


class NativeEnumModel(models.Model):
    str_enum = ChoiceField(StringEnum)
    int_enum = ChoiceField(IntegerEnum)

    class Meta:
        app_label = "test_app"


@admin.register(NativeEnumModel)
class NativeEnumModelAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    ...


class InlinedModel(models.Model):
    class InlinedEnum(Enum):
        VALUE = 0

    inlined_default = ChoiceField(InlinedEnum, default=InlinedEnum.VALUE)
    inlined_enum = ChoiceField(InlinedEnum)


@admin.register(InlinedModel)
class InlinedModelAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    ...
