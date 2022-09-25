from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, TypeVar, cast

from django.core.exceptions import ValidationError
from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models.enums import Choices
from django.db.models.fields import Field
from django.db.models.lookups import Transform
from django.forms import Field as FormField, TypedChoiceField

if TYPE_CHECKING:
    from django.db.models.fields import _ChoicesList

__all__ = ("ChoiceField", "Choice")


T = TypeVar("T", bound=Enum)
M = TypeVar("M", bound=models.Model)


supported_internal_types: Final = MappingProxyType[type, str](
    {
        int: "IntegerField",
        str: "CharField",
    }
)


class Choice:
    __slots__ = ("field",)

    def __init__(self, field: ChoiceField) -> None:
        self.field = field

    def __get__(self, instance: M | None, cls: type[M] | None = None) -> Choice | T:
        if instance is None:
            return self
        elif self.field.attname not in instance.__dict__:
            assert cls is not None
            # We might as well avoid deferring like Django does, as it generates `n+1`
            # that falls silently between the cracks (when e.g. using `.only`)
            raise AttributeError(
                f"Found no value for {self.field.attname!r} on {cls.__qualname__!r} "
                f"instance {str(instance)!r}"
            )

        data = instance.__dict__
        if not isinstance(data[self.field.attname], self.field.enum):
            data[self.field.attname] = self.field.to_python(data[self.field.attname])

        return data[self.field.attname]  # type: ignore[no-any-return]

    def __set__(self, instance: M, value: Any) -> None:
        instance.__dict__[self.field.attname] = self.field.to_python(value)


class ChoiceField(Field):  # type: ignore[type-arg]
    description = "A field storing an enum value"
    descriptor_class = Choice
    empty_strings_allowed = False

    def __init__(self, enum: type[T], *args: Any, **kwargs: Any) -> None:
        self.enum = enum
        self._values = kwargs.pop("_values", None) or tuple(
            member.value for member in self.enum
        )
        # Mypy: IMO `type[T]` should already support `iter()`. As it works for concrete
        # subclasses of `enum.Enum`.
        self.python_type = type(
            next(iter(self.enum)).value  # type: ignore[call-overload]
        )
        try:
            self._internal_type = supported_internal_types[self.python_type]
        except KeyError as exc:
            raise TypeError(
                f"Enum with values of type {self.python_type.__name__!r}"
                f" is not supported"
            ) from exc

        kwargs.setdefault("choices", self.enum_to_choices(self.enum))
        if self._internal_type == "CharField":
            kwargs.setdefault("max_length", 255)
        super().__init__(*args, **kwargs)

    def enum_to_choices(self, enum: type[T]) -> _ChoicesList:
        if hasattr(enum, "choices"):
            # TODO: See https://github.com/typeddjango/django-stubs/pull/1154
            return cast(type[Choices], enum).choices  # type: ignore[return-value]
        return [(member.value, member.name) for member in enum]

    def get_internal_type(self) -> str:
        return self._internal_type

    def from_db_value(
        self, value: Any, expression: Any, connection: Any
    ) -> T | Any | None:
        if isinstance(expression, RawValue):
            return value
        return self.to_python(value)

    def to_python(self, value: Any) -> T | None:
        if isinstance(value, self.enum) or value is None:
            return value
        try:
            return self.enum(self.python_type(value))
        except (ValueError, TypeError) as exc:
            raise ValidationError(str(exc), code="invalid") from exc

    def validate(self, value: Any, model_instance: M | None) -> None:
        if isinstance(value, self.enum):
            # Run validation on enum value instead of enum instance
            # (helps out with validation against `choices`)
            value = value.value
        super().validate(value, model_instance)

    def formfield(self, *args: Any, **kwargs: Any) -> FormField:
        kwargs.setdefault("choices_form_class", ChoiceFormField)
        return super().formfield(*args, **kwargs)  # type: ignore[no-any-return]

    def get_prep_value(self, value: Any) -> Any:
        value = self.to_python(super().get_prep_value(value))
        if isinstance(value, self.enum):
            return value.value
        return value

    def get_db_prep_value(
        self, value: Any, connection: BaseDatabaseWrapper, prepared: bool = False
    ) -> Any:
        prepared_value = super().get_db_prep_value(value, connection, prepared)
        if prepared_value is None and not self.null:
            raise ValidationError(self.error_messages["null"], code="null")
        elif isinstance(prepared_value, self.enum):
            prepared_value = prepared_value.value

        return prepared_value

    def value_to_string(self, obj: M) -> Any:
        value = self.value_from_object(obj)
        return self.get_prep_value(value)

    def deconstruct(self) -> tuple[str, str, Any, Any]:
        name, path, args, kwargs = super().deconstruct()
        if path == "choicefield.fields.ChoiceField":  # pragma: no branch
            path = "choicefield.ChoiceField"
        kwargs.pop("choices", None)
        kwargs["enum"] = self.enum
        kwargs["_values"] = self._values
        return name, path, args, kwargs


@ChoiceField.register_lookup
class RawValue(Transform):
    lookup_name = "raw"
    template = "%(expressions)s"


class ChoiceFormField(TypedChoiceField):
    def prepare_value(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        return value
