import os

COMPANY_NAME = os.getenv(
    "GAIRUS_COMPANY_NAME",
    "Entreprise Gaïrus",
)

LEGAL_FORM = os.getenv(
    "GAIRUS_LEGAL_FORM",
    "SARL",
)

ENTERPRISE_MODE = os.getenv(
    "GAIRUS_ENTERPRISE_MODE",
    "approval",
)

MAX_AUTONOMY_LEVEL = int(
    os.getenv("GAIRUS_MAX_AUTONOMY_LEVEL", "3")
)

REQUIRE_HUMAN_APPROVAL_FOR = {
    "legal_signature",
    "bank_transfer",
    "shareholder_decision",
    "capital_operation",
    "high_value_contract",
    "official_filing",
    "employment_contract",
    "termination",
}
