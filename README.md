<h1 align=center>Django ChoiceField</h1>

<p align=left>
    <a href=https://github.com/flaeppe/django-choicefield/actions?query=workflow%3ACI+branch%3Amain><img src=https://github.com/flaeppe/django-choicefield/workflows/CI/badge.svg alt="CI Build Status"></a>
</p>

### Motivation

Have you also felt annoyed by having to convert
[Django's enumeration types](https://docs.djangoproject.com/en/dev/ref/models/fields/#enumeration-types)
_back_ to its type? Using tricks seen below to cast it.

```python
class Suit(models.IntegerChoices):
    DIAMOND = 1
    SPADE = 2
    HEART = 3
    CLUB = 4


class Card(models.Model):
    suit_kind = models.IntegerField(choices=Suit.choices, db_column="suit")

    @property
    def suit(self) -> Suit:
        return Suit(self.suit_kind)
```

This is what `django-choicefield` helps out with. While it additionally supports using
Python's native [enum.Enum](https://docs.python.org/3/library/enum.html) to express
column values.

### Features

#### Using Django's enumeration types

```python
import choicefield
from django.db import models


class Suit(models.IntegerChoices):
    DIAMOND = 1
    SPADE = 2
    HEART = 3
    CLUB = 4


class Card(models.Model):
    suit = choicefield.ChoiceField(Suit)


instance = Card.objects.create(suit=Suit.CLUB)
assert instance.suit is Suit.CLUB
```

There's also support for Django's `models.TextChoices`.

#### Using Python's native enumeration

```python
import choicefield
from enum import Enum
from django.db import models


class Suit(int, Enum):
    DIAMOND = 1
    SPADE = 2
    HEART = 3
    CLUB = 4


class Card(models.Model):
    suit = choicefield.ChoiceField(Suit)


instance = Card.objects.create(suit=Suit.DIAMOND)
assert instance.suit is Suit.DIAMOND
```

#### Passing enum values

It's also possible to pass the _value_ of an enum, which will be converted to its
corresponding enum instance.

```python
instance = Card(suit=2)
assert instance.suit is Suit.SPADE
instance.save()
assert instance.suit is Suit.SPADE
instance = Card.objects.get(suit=2)
assert instance.suit is Suit.SPADE
```

### Getting stored database values

If you want to access the stored database values, without conversion to your enum type,
you can use the registered `__raw` transformer.

```python
Cart.objects.values("suit__raw")
# <QuerySet [{'suit__raw': 2}]>
```

### Installation

Using `pip`

```console
$ pip install django-choicefield
```

### Running tests

Running the whole test matrix

```console
$ tox
```

Running the test suite for one environment

e.g. `Django==4.0.x` and `Python3.11`

```console
$ tox -e django40-py311
```

### Compatibility

`django-choicefield` is tested according to the table below

| Django version | Python version |
| -------------- | -------------- |
| 4.1.x          | ^3.10          |
| 4.0.x          | ^3.10          |
