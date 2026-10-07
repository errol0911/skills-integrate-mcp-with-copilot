"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
import hashlib
import json
import os
from pathlib import Path
import secrets
import time

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

SESSION_COOKIE = "mergington_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "").lower() in {
    "1", "true", "yes"
}
sessions: dict[str, dict[str, str | float]] = {}


def load_accounts() -> dict[str, dict[str, str]]:
    try:
        configured_accounts = json.loads(os.getenv("ACCOUNTS_JSON", "{}"))
    except json.JSONDecodeError as error:
        raise RuntimeError("ACCOUNTS_JSON must contain valid JSON") from error

    if not isinstance(configured_accounts, dict):
        raise RuntimeError("ACCOUNTS_JSON must be a JSON object")

    accounts = {}
    for email, account in configured_accounts.items():
        if not isinstance(email, str) or not isinstance(account, dict):
            raise RuntimeError("Each account must map an email to an account object")
        role = account.get("role")
        password_hash = account.get("password_hash")
        if role not in {"student", "admin"} or not isinstance(password_hash, str):
            raise RuntimeError("Each account needs a student/admin role and password_hash")
        if not password_hash.startswith("scrypt$"):
            raise RuntimeError("Account passwords must use the supported scrypt format")
        accounts[email.strip().lower()] = {
            "email": email.strip(),
            "role": role,
            "password_hash": password_hash,
        }
    return accounts


accounts = load_accounts()


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
    )
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt_hex, digest_hex = password_hash.split("$")
        if algorithm != "scrypt":
            return False
        salt = bytes.fromhex(salt_hex)
        expected_digest = bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected_digest) != 32:
            return False
        actual_digest = hashlib.scrypt(
            password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=32
        )
        return secrets.compare_digest(actual_digest, expected_digest)
    except (ValueError, TypeError):
        return False


def get_current_account(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, str]:
    session = sessions.get(session_token or "")
    if not session or session["expires_at"] <= time.time():
        sessions.pop(session_token or "", None)
        raise HTTPException(status_code=401, detail="Authentication required")
    return {"email": str(session["email"]), "role": str(session["role"])}


def require_student(
    account: dict[str, str] = Depends(get_current_account),
) -> dict[str, str]:
    if account["role"] != "student":
        raise HTTPException(status_code=403, detail="Student account required")
    return account


def require_admin(
    account: dict[str, str] = Depends(get_current_account),
) -> dict[str, str]:
    if account["role"] != "admin":
        raise HTTPException(status_code=403, detail="Administrator account required")
    return account


# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.post("/auth/login")
def login(credentials: LoginRequest, response: Response):
    account = accounts.get(credentials.email.strip().lower())
    if not account or not verify_password(
        credentials.password, account["password_hash"]
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    session_token = secrets.token_urlsafe(32)
    sessions[session_token] = {
        "email": account["email"],
        "role": account["role"],
        "expires_at": time.time() + SESSION_TTL_SECONDS,
    }
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=SESSION_COOKIE_SECURE,
        samesite="strict",
        path="/",
    )
    return {"email": account["email"], "role": account["role"]}


@app.post("/auth/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
):
    sessions.pop(session_token or "", None)
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"message": "Signed out"}


@app.get("/auth/me")
def get_account(account: dict[str, str] = Depends(get_current_account)):
    return account


@app.get("/activities")
def get_activities():
    return {
        name: {
            "description": activity["description"],
            "schedule": activity["schedule"],
            "max_participants": activity["max_participants"],
            "participant_count": len(activity["participants"]),
        }
        for name, activity in activities.items()
    }


@app.get("/my/activities")
def get_my_activities(account: dict[str, str] = Depends(require_student)):
    email = account["email"]
    return [
        name
        for name, activity in activities.items()
        if email in activity["participants"]
    ]


@app.get("/admin/activities")
def get_admin_activities(account: dict[str, str] = Depends(require_admin)):
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, account: dict[str, str] = Depends(require_student)):
    """Sign up a student for an activity"""
    email = account["email"]
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, account: dict[str, str] = Depends(require_student)):
    """Unregister a student from an activity"""
    email = account["email"]
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
