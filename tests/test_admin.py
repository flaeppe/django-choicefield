import re
from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .test_app.models import (
    ChoiceModel,
    IntChoice,
    IntegerEnum,
    NativeEnumModel,
    StringEnum,
    TextChoice,
)


class TestViews(TestCase):
    user: User
    choice: ChoiceModel
    native: NativeEnumModel

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.user = User.objects.create_superuser(username="test", password="test")
        cls.choice = ChoiceModel.objects.create(
            text_choice=TextChoice.SECOND, int_choice=IntChoice.ONE
        )
        cls.native = NativeEnumModel.objects.create(
            str_enum=StringEnum.B, int_enum=IntegerEnum.FOUR
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.user)

    def test_can_validate_enum_value(self) -> None:
        url = reverse("admin:test_app_choicemodel_change", args=[self.choice.pk])
        response = self.client.get(url)
        data = {"text_choice": 1, "int_choice": 2}
        response = self.client.post(url, data)
        assert response.status_code == HTTPStatus.OK
        assert len(response.context["errors"]) == 1
        assert (
            re.match(
                r".*1 is not one of the available choices.*",
                response.context["errors"][0][0],
            )
            is not None
        )

    def test_can_update_with_enum_value(self) -> None:
        url = reverse("admin:test_app_choicemodel_change", args=[self.choice.pk])
        response = self.client.get(url)
        data = {"text_choice": "FIRST", "int_choice": 2}
        response = self.client.post(url, data, follow=False)
        assert response.status_code == HTTPStatus.FOUND
        self.choice.refresh_from_db(fields=["text_choice", "int_choice"])
        assert self.choice.text_choice is TextChoice.FIRST
        assert self.choice.int_choice is IntChoice.TWO

    def test_renders_form_selections_for_native_enum(self) -> None:
        url = reverse("admin:test_app_nativeenummodel_change", args=[self.native.pk])
        response = self.client.get(url)
        assert response.status_code == HTTPStatus.OK
        self.assertContains(
            response, '<option value="B" selected>B</option>', html=True
        )
        self.assertContains(
            response, '<option value="4" selected>FOUR</option>', html=True
        )
