from decimal import Decimal

from django.core.exceptions import ValidationError


def validate_positive_amount(value):
    if value is None or value < Decimal("0.00"):
        raise ValidationError("Amount must be zero or greater.")


def validate_percentage(value):
    if value is None or not (Decimal("0.00") <= value <= Decimal("100.00")):
        raise ValidationError("Percentage must be between 0 and 100.")


def validate_due_after_issue(issue_date, due_date):
    if due_date < issue_date:
        raise ValidationError("Due date cannot be before issue date.")


def validate_payment_amount_within_remaining(amount, remaining_amount):
    if amount <= Decimal("0.00"):
        raise ValidationError("Payment amount must be greater than zero.")
    if amount > remaining_amount:
        raise ValidationError(
            f"Payment amount ({amount}) exceeds remaining invoice balance "
            f"({remaining_amount})."
        )


def validate_formula_expression(expression: str):
    """
    Whitelist check for formula-based charge rules. Only digits, the
    variable names below, arithmetic operators and parentheses are
    allowed - this is NOT eval()'d until services.FormulaEvaluator
    re-validates and parses it with the same whitelist.
    """
    allowed_tokens = set("0123456789.+-*/() ") | {
        "area", "persons", "units", "base"
    }
    cleaned = expression
    for word in ("area", "persons", "units", "base"):
        cleaned = cleaned.replace(word, "")
    if not set(cleaned) <= set("0123456789.+-*/() "):
        raise ValidationError(
            "Formula contains disallowed characters. Allowed variables: "
            "area, persons, units, base."
        )
