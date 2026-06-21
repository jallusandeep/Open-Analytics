from .common import *  # noqa: F401,F403


def parse_upstox_error(error_body: str):
    try:
        payload = json.loads(error_body)
    except Exception:
        return {
            "raw": error_body,
            "error_code": None,
            "message": error_body
        }

    errors = payload.get("errors")

    if isinstance(errors, list) and errors:
        first_error = errors[0] or {}

        return {
            "raw": payload,
            "error_code": (
                first_error.get("errorCode")
                or first_error.get("error_code")
                or first_error.get("code")
            ),
            "message": first_error.get("message") or str(payload)
        }

    return {
        "raw": payload,
        "error_code": (
            payload.get("errorCode")
            or payload.get("error_code")
            or payload.get("code")
        ),
        "message": payload.get("message") or str(payload)
    }


def is_expired_permission_error(error_code, message: str) -> bool:
    lowered_message = (message or "").lower()

    return (
        error_code == "UDAPI100067"
        or "read only token" in lowered_message
        or "permission" in lowered_message
        or "not authorized" in lowered_message
        or "not authorised" in lowered_message
        or "scope" in lowered_message
        or "upstox plus" in lowered_message
        or "expired instruments api" in lowered_message
    )


def upstox_api_get(access_token: str, path: str, params=None):
    token = normalize_upstox_token(access_token)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox access token is required."
        )

    query_string = ""

    if params:
        query_string = "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        f"{UPSTOX_BASE_URL}{path}{query_string}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"],
                "error_code": parsed_error["error_code"],
                "raw": parsed_error["raw"]
            }
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox API."
        )


def upstox_public_api_get(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")

        raise HTTPException(
            status_code=error.code,
            detail=f"Unable to download Upstox public instruments: {error_body}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox public instruments CDN: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON received from Upstox public instruments CDN."
        )


def upstox_token_post(payload: dict):
    encoded_payload = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(
        UPSTOX_TOKEN_URL,
        data=encoded_payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"],
                "error_code": parsed_error["error_code"],
                "raw": parsed_error["raw"]
            }
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox token API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox token API."
        )


def upstox_access_token_request_post(client_id: str, client_secret: str):
    clean_client_id = safe_strip(client_id)
    clean_client_secret = safe_strip(client_secret)

    if not clean_client_id or not clean_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox API key and API secret are required to request access token approval."
        )

    request_url = (
        f"{UPSTOX_ACCESS_TOKEN_REQUEST_BASE_URL}/"
        f"{urllib.parse.quote(clean_client_id, safe='')}"
    )

    encoded_payload = json.dumps({
        "client_secret": clean_client_secret
    }).encode("utf-8")

    request = urllib.request.Request(
        request_url,
        data=encoded_payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"],
                "error_code": parsed_error["error_code"],
                "raw": parsed_error["raw"]
            }
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox access token request API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox access token request API."
        )


def download_upstox_active_instruments(exchange: str = "complete"):
    exchange_code = safe_strip(exchange) if exchange else "complete"

    if not exchange_code:
        exchange_code = "complete"

    url = f"{UPSTOX_PUBLIC_INSTRUMENTS_BASE_URL}/{exchange_code}.json"
    return upstox_public_api_get(url)


def validate_upstox_expired_permission(access_token: str):
    try:
        return upstox_api_get(
            access_token=access_token,
            path=UPSTOX_EXPIRED_PERMISSION_TEST_PATH,
            params={
                "instrument_key": UPSTOX_EXPIRED_PERMISSION_TEST_KEY
            }
        )

    except HTTPException as primary_error:
        primary_detail = primary_error.detail
        primary_error_code = None
        primary_message = ""

        if isinstance(primary_detail, dict):
            primary_error_code = primary_detail.get("error_code")
            primary_message = primary_detail.get("message") or ""
        else:
            primary_message = str(primary_detail)

        if is_expired_permission_error(primary_error_code, primary_message):
            raise

        if primary_error.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Upstox token is invalid or expired. Please save a fresh token."
            )

        return upstox_api_get(
            access_token=access_token,
            path=UPSTOX_EXPIRED_PERMISSION_TEST_PATH,
            params={
                "instrument_key": UPSTOX_EXPIRED_PERMISSION_TEST_KEY
            }
        )


def get_upstox_expired_option_contracts(
    access_token: str,
    instrument_key: str,
    expiry_date: str
):
    return upstox_api_get(
        access_token=access_token,
        path=UPSTOX_EXPIRED_OPTION_CONTRACT_PATH,
        params={
            "instrument_key": instrument_key,
            "expiry_date": expiry_date
        }
    )


def get_upstox_expired_future_contracts(
    access_token: str,
    instrument_key: str,
    expiry_date: str
):
    return upstox_api_get(
        access_token=access_token,
        path=UPSTOX_EXPIRED_FUTURE_CONTRACT_PATH,
        params={
            "instrument_key": instrument_key,
            "expiry_date": expiry_date
        }
    )


def get_upstox_expired_historical_candles(
    access_token: str,
    expired_instrument_key: str,
    interval: str,
    to_date: str,
    from_date: str
):
    safe_expired_instrument_key = urllib.parse.quote(
        expired_instrument_key,
        safe=""
    )

    safe_interval = urllib.parse.quote(interval, safe="")
    safe_to_date = urllib.parse.quote(to_date, safe="")
    safe_from_date = urllib.parse.quote(from_date, safe="")

    path = (
        f"{UPSTOX_EXPIRED_HISTORICAL_CANDLE_PATH}/"
        f"{safe_expired_instrument_key}/"
        f"{safe_interval}/"
        f"{safe_to_date}/"
        f"{safe_from_date}"
    )

    return upstox_api_get(
        access_token=access_token,
        path=path
    )
