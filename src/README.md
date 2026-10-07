# Mergington High School Activities

A FastAPI application for browsing extracurricular activities and signing up with authenticated student accounts.

## Features

- View all available extracurricular activities
- Sign in as a student or administrator
- Sign up for activities using the signed-in student identity
- View participant rosters only as an administrator

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Generate a scrypt password hash for each account:

   ```
   python account_tools.py --email student@mergington.edu --role student
   ```

   The helper prompts for a password and prints a JSON account entry. Repeat for each account, then provide the complete JSON object through the `ACCOUNTS_JSON` environment variable. Supply this variable through your deployment's secret manager; do not commit account credentials or hashes. To reset an account, generate a new hash, update the secret, and restart the application. There is no public account-creation or password-recovery endpoint.

3. Run the application from this directory:

   ```
   uvicorn app:app --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                 | Description                                                    |
| ------ | ---------------------------------------- | -------------------------------------------------------------- |
| POST   | `/auth/login`                            | Sign in with a provisioned email and password                  |
| POST   | `/auth/logout`                           | Revoke the current session                                     |
| GET    | `/auth/me`                               | Get the current account                                        |
| GET    | `/activities`                            | List activities and participant counts without roster details |
| GET    | `/admin/activities`                      | Get participant rosters (administrator only)                  |
| POST   | `/activities/{activity_name}/signup`     | Sign up the authenticated student                              |
| DELETE | `/activities/{activity_name}/unregister` | Unregister the authenticated student                           |

Sessions expire after eight hours and are kept in process memory, so they are revoked when the server restarts. Run a single application process; multi-worker deployments require a shared session store. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS. The application has no separate administrative mutation or roster-export endpoints yet; any such endpoints must enforce the administrator role server-side.

Activity and signup data remain in memory and reset when the server restarts.
