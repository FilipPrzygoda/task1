import pytest

from project.customers.models import Customer


def make_customer(**overrides):
    values = {
        'name': 'Ada Lovelace',
        'city': 'London',
        'age': 36,
    }
    values.update(overrides)
    return Customer(**values)


def test_customer_accepts_valid_values():
    customer = make_customer()

    assert customer.name == 'Ada Lovelace'
    assert customer.city == 'London'
    assert customer.age == 36


@pytest.mark.parametrize('field', ('name', 'city', 'age'))
@pytest.mark.parametrize(
    'payload',
    (
        '<script>alert(1)</script>',
        '<svg onload=alert(1)>',
    ),
)
def test_customer_rejects_xss_input(field, payload):
    with pytest.raises(ValueError):
        make_customer(**{field: payload})
