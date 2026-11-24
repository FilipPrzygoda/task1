from datetime import date

import pytest

from project.books.models import BOOK_TYPES
from project.loans.models import Loan


def make_loan(**overrides):
    values = {
        'customer_name': 'Ada Lovelace',
        'book_name': 'Władca Pierścieni',
        'loan_date': date(2026, 1, 1),
        'return_date': date(2026, 1, 10),
        'original_author': 'J.R.R. Tolkien',
        'original_year_published': 1954,
        'original_book_type': BOOK_TYPES[0],
    }
    values.update(overrides)
    return Loan(**values)


def test_loan_accepts_valid_values():
    loan = make_loan()

    assert loan.customer_name == 'Ada Lovelace'
    assert loan.book_name == 'Władca Pierścieni'
    assert loan.original_author == 'J.R.R. Tolkien'
    assert loan.original_year_published == 1954
    assert loan.original_book_type == BOOK_TYPES[0]


@pytest.mark.parametrize(
    'field',
    (
        'customer_name',
        'book_name',
        'loan_date',
        'return_date',
        'original_author',
        'original_year_published',
        'original_book_type',
    ),
)
@pytest.mark.parametrize(
    'payload',
    (
        '<script>alert(1)</script>',
        '<img src=x onerror=alert(1)>',
    ),
)
def test_loan_rejects_xss_input(field, payload):
    with pytest.raises(ValueError):
        make_loan(**{field: payload})
