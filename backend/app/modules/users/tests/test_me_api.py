"""/api/v1/users/me — the signed-in user's profile and onboarding answers."""

from httpx import AsyncClient


async def test_me_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/v1/users/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "common.unauthorized"


async def test_get_me(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/users/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["locale"] == "uz" and body["role"] == "user" and body["onboarding_completed_at"] is None


async def test_onboarding_answers_and_completion(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    r = await client.patch(
        "/api/v1/users/me",
        json={
            "locale": "ja",
            "residence_country": "JP",
            "timezone": "Asia/Tokyo",
            "jlpt_level": "n3",
            "goal": "work",
            "onboarding_completed": True,
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert (body["locale"], body["residence_country"], body["timezone"]) == ("ja", "JP", "Asia/Tokyo")
    assert (body["jlpt_level"], body["goal"]) == ("n3", "work")
    assert body["onboarding_completed_at"] is not None

    r = await client.patch("/api/v1/users/me", json={"goal": None, "display_name": None}, headers=auth_headers)
    assert r.json()["goal"] is None  # optional answer cleared
    assert r.json()["display_name"] == "Test User"  # required field kept


async def test_invalid_values_are_validation_codes(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    for payload in ({"timezone": "Mars/Base"}, {"residence_country": "jp"}, {"role": "admin"}, {"display_name": " "}):
        r = await client.patch("/api/v1/users/me", json=payload, headers=auth_headers)
        assert r.status_code == 422, payload
        assert r.json()["error"]["code"] == "common.validation"
