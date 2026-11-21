# Mobile Auth0 — Callback URL mismatch (fix now)

Auth0 error: **“The provided redirect_uri is not in the list of allowed callback URLs.”**

## Fix (2 minutes)

1. Open Auth0 Dashboard → **Applications** → the app whose Client ID is in `room-ready/.env`  
   (prefer a **Native** application).
2. Open **Settings** → **Application URIs**.
3. **Allowed Callback URLs** — paste **all** of these (comma or newline separated):

```text
roomready://auth/callback
exp://192.168.1.6:8081/--/auth/callback
exp://127.0.0.1:8081/--/auth/callback
exp://localhost:8081/--/auth/callback
http://localhost:8081
http://localhost:8081/
http://localhost:8081/auth/callback
http://127.0.0.1:8081
http://127.0.0.1:8081/auth/callback
```

4. **Allowed Logout URLs:**

```text
roomready://
http://localhost:8081
```

5. Click **Save Changes**.
6. In the app: Sign in screen shows the **exact** redirect URI — if it is different, add that line too.
7. Reload Expo → **Continue with organisation login** again.

## If PC IP changes

Run `ipconfig`, then update the `exp://YOUR_IP:8081/--/auth/callback` line.

Optional override in `room-ready/.env`:

```env
EXPO_PUBLIC_AUTH0_REDIRECT_URI=roomready://auth/callback
```

(Expo Go often still uses `exp://…` — prefer adding the URI shown on the Sign in screen.)

## Web backup for boss meeting

http://localhost:3000/auth/login
