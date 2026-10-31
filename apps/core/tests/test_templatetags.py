from django.template import Context, Template

from apps.core.templatetags.persian import persian_digits


def test_digits_become_persian():
    assert persian_digits(1234567890) == "\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u06f0"


def test_other_characters_are_left_alone():
    assert persian_digits("12 abc \u062a") == "\u06f1\u06f2 abc \u062a"


def test_it_is_available_to_templates_as_a_filter():
    template = Template("{% load persian %}{{ n|persian_digits }}")
    assert template.render(Context({"n": 30})) == "\u06f3\u06f0"
