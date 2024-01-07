from enum import Enum
from typing import Any, TypeVar

import pytest
from django.core import serializers
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.db.models.expressions import Value
from django.test import TestCase

from choicefield import ChoiceField
from choicefield.fields import Choice

from .test_app.models import (
    ChoiceModel,
    InlinedModel,
    IntChoice,
    IntEnum,
    NativeEnumModel,
    NullableModel,
    StrEnum,
    TextChoice,
)

M = TypeVar("M", bound=models.Model)


@pytest.mark.django_db()
class TestSave:
    @pytest.mark.parametrize(
        "Model",
        [
            pytest.param(ChoiceModel, id="django_enum_instance"),
            pytest.param(NativeEnumModel, id="native_enum_instance"),
            pytest.param(InlinedModel, id="inlined_enum_instance"),
        ],
    )
    def test_errors_saving_unpopulated(self, Model: type[M]) -> None:
        unsaved = Model()
        with pytest.raises(ValidationError, match=r"field cannot be null"):
            unsaved.save()

    def test_can_save_to_database_with_enum(self) -> None:
        choice = ChoiceModel.objects.create(
            text_choice=TextChoice.SECOND, int_choice=IntChoice.ONE
        )
        assert choice.text_choice is TextChoice.SECOND
        assert choice.int_choice is IntChoice.ONE
        choice.refresh_from_db(fields=["text_choice", "int_choice"])

        native = NativeEnumModel.objects.create(
            str_enum=StrEnum.A, int_enum=IntEnum.THREE
        )
        assert native.str_enum is StrEnum.A
        assert native.int_enum is IntEnum.THREE
        native.refresh_from_db(fields=["str_enum", "int_enum"])

    def test_can_save_to_database_with_enum_value(self) -> None:
        choice = ChoiceModel.objects.create(text_choice="SECOND", int_choice=1)
        assert choice.text_choice is TextChoice.SECOND
        assert choice.int_choice is IntChoice.ONE
        choice.refresh_from_db(fields=["text_choice", "int_choice"])
        assert choice.text_choice is TextChoice.SECOND
        assert choice.int_choice is IntChoice.ONE

        native = NativeEnumModel.objects.create(str_enum="A", int_enum=3)
        assert native.str_enum is StrEnum.A
        assert native.int_enum is IntEnum.THREE
        native.refresh_from_db(fields=["str_enum", "int_enum"])
        assert native.str_enum is StrEnum.A
        assert native.int_enum is IntEnum.THREE

    def test_can_build_and_save_with_enum(self) -> None:
        choice = ChoiceModel()
        choice.text_choice = TextChoice.FIRST
        choice.int_choice = IntChoice.TWO
        choice.save()
        choice.refresh_from_db(fields=["text_choice", "int_choice"])
        assert choice.text_choice is TextChoice.FIRST
        assert choice.int_choice is IntChoice.TWO

        native = NativeEnumModel()
        native.str_enum = StrEnum.B
        native.int_enum = IntEnum.FOUR
        native.save()
        native.refresh_from_db(fields=["str_enum", "int_enum"])
        assert native.str_enum is StrEnum.B
        assert native.int_enum is IntEnum.FOUR

    def test_raises_validation_error_saving_with_unknown_enum_value(self) -> None:
        with pytest.raises(
            ValidationError, match=r"'THIRD' is not a valid TextChoice"
        ) as exc:
            ChoiceModel.objects.create(text_choice="THIRD", int_choice=1)
        assert exc.value.code == "invalid"

        with pytest.raises(ValidationError, match=r"3 is not a valid IntChoice") as exc:
            ChoiceModel.objects.create(text_choice="FIRST", int_choice=3)
        assert exc.value.code == "invalid"

        with pytest.raises(ValidationError, match=r"'C' is not a valid StrEnum") as exc:
            NativeEnumModel.objects.create(str_enum="C", int_enum=3)
        assert exc.value.code == "invalid"

        with pytest.raises(ValidationError, match=r"1 is not a valid IntEnum") as exc:
            NativeEnumModel.objects.create(str_enum="A", int_enum=1)
        assert exc.value.code == "invalid"

    def test_casts_to_enum_type_from_db_value(self) -> None:
        ChoiceModel.objects.create(
            text_choice=TextChoice.FIRST, int_choice=IntChoice.TWO
        )
        instance = ChoiceModel.objects.get()
        assert instance.text_choice is TextChoice.FIRST
        assert instance.int_choice is IntChoice.TWO

    def test_defaults_nullable_field_to_none(self) -> None:
        assert NullableModel.objects.create().choice is None

    def test_can_save_with_inlined_enum(self) -> None:
        instance = InlinedModel.objects.create(
            inlined_enum=InlinedModel.InlinedEnum.VALUE
        )
        assert instance.inlined_enum is InlinedModel.InlinedEnum.VALUE
        assert instance.inlined_default is InlinedModel.InlinedEnum.VALUE

    def test_can_save_with_default(self) -> None:
        instance = InlinedModel.objects.create(
            inlined_enum=InlinedModel.InlinedEnum.VALUE
        )
        assert instance.inlined_default is InlinedModel.InlinedEnum.VALUE


class TestFilter(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        ChoiceModel.objects.create(
            text_choice=TextChoice.FIRST, int_choice=IntChoice.TWO
        )
        NativeEnumModel.objects.create(str_enum=StrEnum.B, int_enum=IntEnum.FOUR)
        NullableModel.objects.create()
        InlinedModel.objects.create(inlined_enum=InlinedModel.InlinedEnum.VALUE)

    def test_can_equals_filter_on_enum(self) -> None:
        assert ChoiceModel.objects.filter(text_choice=TextChoice.FIRST).exists() is True
        assert (
            ChoiceModel.objects.filter(text_choice=TextChoice.SECOND).exists() is False
        )

        assert ChoiceModel.objects.filter(int_choice=IntChoice.TWO).exists() is True
        assert ChoiceModel.objects.filter(int_choice=IntChoice.ONE).exists() is False

    def test_can_equals_filter_on_enum_value(self) -> None:
        assert ChoiceModel.objects.filter(text_choice="FIRST").exists() is True
        assert ChoiceModel.objects.filter(text_choice="SECOND").exists() is False

        assert ChoiceModel.objects.filter(int_choice=2).exists() is True
        assert ChoiceModel.objects.filter(int_choice=1).exists() is False

    def test_can_filter_in_enum(self) -> None:
        assert ChoiceModel.objects.filter(int_choice__in=IntChoice).exists() is True
        assert ChoiceModel.objects.filter(text_choice__in=TextChoice).exists() is True

    def test_can_filter_equals_none(self) -> None:
        assert NullableModel.objects.filter(choice=None).exists() is True

    def test_can_filter_unknown_values_with_raw(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE test_app_nativeenummodel SET str_enum = "UNKNOWN",'
                " int_enum = 1337"
            )
            cursor.execute(
                'UPDATE test_app_choicemodel SET text_choice = "UNKNOWN",'
                " int_choice = 1337"
            )
            cursor.execute(
                "UPDATE test_app_inlinedmodel SET inlined_default = 1337,"
                " inlined_enum = 1338"
            )

        choices = ChoiceModel.objects.filter(
            text_choice=Value("UNKNOWN"), int_choice=Value(1337)
        ).values_list("text_choice__raw", "int_choice__raw")
        assert list(choices) == [("UNKNOWN", 1337)]

        natives = NativeEnumModel.objects.filter(
            str_enum=Value("UNKNOWN"), int_enum=Value(1337)
        ).values_list("str_enum__raw", "int_enum__raw")
        assert list(natives) == [("UNKNOWN", 1337)]

        inlines = InlinedModel.objects.filter(
            inlined_default=Value(1337), inlined_enum=Value(1338)
        ).values_list("inlined_default__raw", "inlined_enum__raw")
        assert list(inlines) == [(1337, 1338)]


class TestUpdate(TestCase):
    instance: ChoiceModel

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.instance = ChoiceModel.objects.create(
            text_choice=TextChoice.SECOND, int_choice=IntChoice.ONE
        )

    def test_can_do_database_update_with_enum(self) -> None:
        assert (
            ChoiceModel.objects.update(
                text_choice=TextChoice.FIRST, int_choice=IntChoice.TWO
            )
            == 1
        )

    def test_can_do_database_update_with_enum_value(self) -> None:
        assert (
            ChoiceModel.objects.filter(
                text_choice=TextChoice.FIRST, int_choice=IntChoice.TWO
            ).exists()
            is False
        )
        assert ChoiceModel.objects.update(text_choice="FIRST", int_choice=2) == 1
        assert (
            ChoiceModel.objects.filter(
                text_choice=TextChoice.FIRST, int_choice=IntChoice.TWO
            ).exists()
            is True
        )

    def test_errors_updating_to_unknown_value(self) -> None:
        with pytest.raises(
            ValidationError, match=r"'UNKNOWN' is not a valid TextChoice"
        ):
            ChoiceModel.objects.update(text_choice="UNKNOWN")
        with pytest.raises(ValidationError, match=r"1337 is not a valid IntChoice"):
            ChoiceModel.objects.update(int_choice=1337)
        with pytest.raises(ValidationError, match=r"1337 is not a valid IntChoice"):
            NullableModel.objects.update(choice=1337)
        with pytest.raises(ValidationError, match=r"'UNKNOWN' is not a valid StrEnum"):
            NativeEnumModel.objects.update(str_enum="UNKNOWN")
        with pytest.raises(ValidationError, match=r"1337 is not a valid IntEnum"):
            NativeEnumModel.objects.update(int_enum=1337)
        with pytest.raises(
            ValidationError, match=r"1337 is not a valid InlinedModel.InlinedEnum"
        ):
            InlinedModel.objects.update(inlined_default=1337)
        with pytest.raises(
            ValidationError, match=r"1337 is not a valid InlinedModel.InlinedEnum"
        ):
            InlinedModel.objects.update(inlined_enum=1337)

    def test_can_do_application_update_with_enum(self) -> None:
        self.instance.text_choice = TextChoice.FIRST
        self.instance.int_choice = IntChoice.TWO
        assert self.instance.text_choice is TextChoice.FIRST
        assert self.instance.int_choice is IntChoice.TWO

        self.instance.save(update_fields=["text_choice", "int_choice"])
        assert self.instance.text_choice is TextChoice.FIRST
        assert self.instance.int_choice is IntChoice.TWO

        self.instance.refresh_from_db(fields=["text_choice", "int_choice"])
        assert self.instance.text_choice is TextChoice.FIRST
        assert self.instance.int_choice is IntChoice.TWO

    def test_can_do_application_update_with_enum_value(self) -> None:
        self.instance.text_choice = "FIRST"
        self.instance.int_choice = 2
        assert self.instance.text_choice is TextChoice.FIRST
        assert self.instance.int_choice is IntChoice.TWO

        self.instance.save(update_fields=["text_choice", "int_choice"])
        assert self.instance.text_choice is TextChoice.FIRST
        assert self.instance.int_choice is IntChoice.TWO

        self.instance.refresh_from_db(fields=["text_choice", "int_choice"])
        assert self.instance.text_choice is TextChoice.FIRST
        assert self.instance.int_choice is IntChoice.TWO

    def test_can_do_database_update_to_null(self) -> None:
        NullableModel.objects.create(choice=IntChoice.TWO)
        assert NullableModel.objects.update(choice=None) == 1

    def test_can_do_application_update_to_null(self) -> None:
        instance = NullableModel.objects.create(choice=IntChoice.TWO)
        instance.choice = None
        instance.save(update_fields=["choice"])
        assert instance.choice is None
        instance.refresh_from_db(fields=["choice"])
        assert instance.choice is None


class TestChoiceDescriptor(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        ChoiceModel.objects.create(
            text_choice=TextChoice.SECOND, int_choice=IntChoice.ONE
        )

    def test_returns_descriptor_accessing_model_class(self) -> None:
        assert isinstance(ChoiceModel.int_choice, Choice) is True

    def test_errors_when_value_is_not_loaded_from_db(self) -> None:
        instance = ChoiceModel.objects.only("int_choice").get()
        with pytest.raises(AttributeError, match=r"Found no value"):
            assert instance.text_choice is TextChoice.SECOND


class TestChoiceField:
    def test_raises_value_error_on_unsupported_enum_value_type(self) -> None:
        class Unsupported(Enum):
            LIST = [1]

        with pytest.raises(
            TypeError, match=r"Enum with values of type 'list' is not supported"
        ):
            ChoiceField(Unsupported)

    def test_can_customise_max_length_for_str_based_enum(self) -> None:
        field = ChoiceField(TextChoice, max_length=30)
        assert field.max_length == 30

    def test_can_customise_choices(self) -> None:
        field = ChoiceField(TextChoice, choices=[("SECOND", "second")])
        assert field.choices == [("SECOND", "second")]

    def test_deconstruct_includes_enum(self) -> None:
        instance = ChoiceField(TextChoice)
        __, ___, args, kwargs = instance.deconstruct()
        new = ChoiceField(*args, **kwargs)
        assert new.enum == instance.enum
        assert new.enum is TextChoice

    def test_deconstruct_excludes_choices(self) -> None:
        instance = ChoiceField(IntChoice, choices=[("ONE", "one")])
        __, ___, args, kwargs = instance.deconstruct()
        assert "choices" not in kwargs

    def test_unsaved_unpopulated_instance_defaults_value_to_none(self) -> None:
        # We need to be able to instantiate unsaved models (for e.g. "Add" in admin).
        # But we want to ensure that we won't use an empty string(""), since that'll
        # break our descriptor class.
        choice = ChoiceModel()
        assert choice.text_choice is None
        assert choice.int_choice is None
        nullable = NullableModel()
        assert nullable.choice is None
        native = NativeEnumModel()
        assert native.str_enum is None
        assert native.int_enum is None
        inlined = InlinedModel()
        assert inlined.inlined_enum is None

    def test_can_set_field_value_to_none(self) -> None:
        choice = ChoiceModel()
        choice.text_choice = None

    def test_errors_setting_non_int_enum_to_string_value(self) -> None:
        choice = ChoiceModel()
        with pytest.raises(ValidationError, match=r"invalid literal"):
            choice.int_choice = "abc"

    def test_can_validate_with_non_enum_value(self) -> None:
        field = ChoiceField(IntChoice)
        with pytest.raises(ValidationError, match=r"1337 is not a valid choice"):
            field.validate(value=1337, model_instance=None)

    def test_get_db_prep_value_handles_prepared_enum(self) -> None:
        value = ChoiceField(InlinedModel.InlinedEnum).get_db_prep_value(
            value=InlinedModel.InlinedEnum.VALUE,
            connection=None,  # type: ignore[arg-type]
            prepared=True,
        )
        assert value == 0


class TestSerialization(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        ChoiceModel.objects.create(
            text_choice=TextChoice.SECOND, int_choice=IntChoice.ONE
        )
        NullableModel.objects.create()
        NativeEnumModel.objects.create(str_enum=StrEnum.B, int_enum=IntEnum.FOUR)
        InlinedModel.objects.create(inlined_enum=InlinedModel.InlinedEnum.VALUE)

    def serialize_and_parse(self, queryset: models.QuerySet[models.Model]) -> list[Any]:
        return list(
            serializers.deserialize("json", serializers.serialize("json", queryset))
        )

    def test_can_serialize_and_parse(self) -> None:
        choices = self.serialize_and_parse(ChoiceModel.objects.all())
        assert len(choices) == 1
        assert choices[0].object.text_choice is TextChoice.SECOND
        assert choices[0].object.int_choice is IntChoice.ONE

        natives = self.serialize_and_parse(NativeEnumModel.objects.all())
        assert len(natives) == 1
        assert natives[0].object.str_enum is StrEnum.B
        assert natives[0].object.int_enum is IntEnum.FOUR

        inlines = self.serialize_and_parse(InlinedModel.objects.all())
        assert len(inlines) == 1
        assert inlines[0].object.inlined_enum is InlinedModel.InlinedEnum.VALUE

    def test_raw_lookup_returns_enum_values(self) -> None:
        choices = ChoiceModel.objects.values("text_choice__raw", "int_choice__raw")
        assert list(choices) == [{"text_choice__raw": "SECOND", "int_choice__raw": 1}]
        nullables = NullableModel.objects.values("choice__raw")
        assert list(nullables) == [{"choice__raw": None}]
        natives = NativeEnumModel.objects.values("str_enum__raw", "int_enum__raw")
        assert list(natives) == [{"str_enum__raw": "B", "int_enum__raw": 4}]
        inlines = InlinedModel.objects.values(
            "inlined_default__raw", "inlined_enum__raw"
        )
        assert list(inlines) == [{"inlined_default__raw": 0, "inlined_enum__raw": 0}]

    def test_raw_lookup_returns_stored_values(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                'UPDATE test_app_choicemodel SET text_choice = "UNKNOWN",'
                " int_choice = 1337"
            )

        choices = ChoiceModel.objects.values("text_choice__raw", "int_choice__raw")
        assert list(choices) == [
            {"text_choice__raw": "UNKNOWN", "int_choice__raw": 1337}
        ]

    def test_queryset_values_returns_enum_instances(self) -> None:
        choices = ChoiceModel.objects.values("text_choice", "int_choice")
        assert list(choices) == [
            {"text_choice": TextChoice.SECOND, "int_choice": IntChoice.ONE}
        ]
        nullables = NullableModel.objects.values("choice")
        assert list(nullables) == [{"choice": None}]
        natives = NativeEnumModel.objects.values("str_enum", "int_enum")
        assert list(natives) == [{"str_enum": StrEnum.B, "int_enum": IntEnum.FOUR}]
        inlines = InlinedModel.objects.values("inlined_default", "inlined_enum")
        assert list(inlines) == [
            {
                "inlined_default": InlinedModel.InlinedEnum.VALUE,
                "inlined_enum": InlinedModel.InlinedEnum.VALUE,
            }
        ]

    def test_errors_fetching_row_with_unknown_enum_value(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute('UPDATE test_app_choicemodel SET text_choice = "UNKNOWN"')

        with pytest.raises(
            ValidationError, match=r"'UNKNOWN' is not a valid TextChoice"
        ):
            list(ChoiceModel.objects.values())
