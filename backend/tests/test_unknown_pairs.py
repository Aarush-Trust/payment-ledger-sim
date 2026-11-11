"""Unknown currency pairs are rejected with 422. They never convert at a made-up rate of 1.0."""
import uuid

import pytest

# The eight supported pairs and what each one converted to before the fix, written out literally
# (not read back from RATES) so a change to the table or to convert() shows up here.
EXPECTED = [
    ("USD", "EUR", 0.9, 90.0),
    ("EUR", "USD", 1.1, 110.00000000000001),
    ("CAD", "USD", 0.7, 70.0),
    ("USD", "CAD", 1.4, 140.0),
    ("USD", "BTC", 1 / 50000, 100 * (1 / 50000)),
    ("BTC", "USD", 50000.0, 5000000.0),
    ("EUR", "BTC", 1 / 55000, 100 * (1 / 55000)),
    ("BTC", "EUR", 55000.0, 5500000.0),
]


def post_tx(client, auth, source, target, key=None, amount=100):
    return client.post(
        "/transactions",
        headers=auth,
        json={
            "amount": amount,
            "source_currency": source,
            "target_currency": target,
            "idempotency_key": key or f"k-{uuid.uuid4().hex}",
        },
    )


@pytest.mark.parametrize("source,target", [("CAD", "EUR"), ("EUR", "CAD"), ("USD", "XYZ"), ("XYZ", "USD"), ("GBP", "JPY")])
def test_unknown_pair_is_422_in_the_existing_error_format(client, auth, source, target):
    response = post_tx(client, auth, source, target)
    assert response.status_code == 422
    body = response.json()
    # Same shape as the API's other errors (HTTPException): {"detail": "<message>"}
    assert list(body.keys()) == ["detail"]
    assert isinstance(body["detail"], str)
    assert source in body["detail"] and target in body["detail"]


def test_unknown_pair_with_lowercase_input_is_still_rejected(client, auth):
    assert post_tx(client, auth, "usd", "xyz").status_code == 422


def test_rejected_request_writes_nothing(client, auth):
    before = len(client.get("/transactions", headers=auth).json())
    assert post_tx(client, auth, "CAD", "EUR").status_code == 422
    assert post_tx(client, auth, "USD", "XYZ").status_code == 422
    after = len(client.get("/transactions", headers=auth).json())
    assert before == after == 0


def test_rejected_key_can_be_reused_with_a_supported_pair(client, auth):
    assert post_tx(client, auth, "CAD", "EUR", key="same-key").status_code == 422
    retry = post_tx(client, auth, "CAD", "USD", key="same-key")
    assert retry.status_code == 201
    assert retry.json()["rate"] == 0.7


@pytest.mark.parametrize("source,target,rate,converted", EXPECTED)
def test_all_eight_supported_pairs_convert_exactly_as_before(client, auth, source, target, rate, converted):
    response = post_tx(client, auth, source, target, amount=100)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["rate"] == rate
    assert body["converted_amount"] == converted
    assert body["source_currency"] == source
    assert body["target_currency"] == target
    assert body["status"] == "COMPLETED"


def test_same_currency_still_converts_one_to_one(client, auth):
    # Not an unknown pair and not a fallback: the identity conversion is unchanged.
    body = post_tx(client, auth, "USD", "USD", amount=42).json()
    assert body["rate"] == 1.0 and body["converted_amount"] == 42
