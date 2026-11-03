# How `servicetitan.py` Works

## Likely Broken Link

The likely source of confusion is expecting this file to actually do something when you run the app. It doesn't — not yet. Almost all of it is placeholder code (marked `TODO`) that will do nothing until someone supplies API credentials and finishes the implementation. Understanding that this file is a stub (a reserved slot for future functionality) rather than live code is the key.

---

## Rebuild

### What This File Is For

ServiceTitan is the job management software the company uses to track estimates, jobs, and customers. The goal of this file is to eventually connect the pricing app directly to ServiceTitan in two directions:

1. **Pull** — when an estimator enters a ServiceTitan Job ID, the app would automatically fill in the job's cost details from ServiceTitan so they don't have to type them manually.
2. **Push** — after an estimator submits a bid decision, the app would write the flag result, benchmark price, and reason code back into the ServiceTitan estimate as custom fields.

Neither direction is active yet.

---

### The On/Off Switch

At the very top of the file is one line:

```python
SERVICETITAN_ENABLED = False
```

This single variable acts as a master switch. Every function in the file checks it first. If `False`, the function immediately exits without doing anything. The rest of the app reads this variable too — `app.py` imports it to decide whether to show "ServiceTitan: Connected" or a grayed-out "Not Connected" badge in the sidebar.

When the time comes to activate the integration, step one is changing `False` to `True` here.

---

### Authentication: `_get_token()`

Before any software can talk to ServiceTitan's servers, it has to prove it has permission. ServiceTitan uses a standard security protocol called **OAuth2** — the same kind of "sign in with Google" flow you see on websites, adapted for software-to-software communication.

The process works like this:
1. Your software sends its `client_id` and `client_secret` (like a username and password for the app itself) to ServiceTitan's authentication server.
2. ServiceTitan responds with a short-lived **bearer token** — a temporary string that proves you're authorized for the next hour or so.
3. Every subsequent request includes that token in its header, so ServiceTitan knows the request is legitimate.

`_get_token()` is where step 1 and 2 would happen. Right now it contains only a comment describing what to do and a `raise NotImplementedError` line, which is Python's way of saying "this function exists but isn't written yet — if you call it, crash intentionally rather than behave unpredictably."

---

### Pushing Data: `push_job_flag()`

This function would write the app's outputs — the flag color, benchmark price, deviation, reason code — back into the ServiceTitan estimate as custom fields. Think of it as the app annotating the original estimate record so everyone in ServiceTitan can see the pricing review outcome.

The technical mechanism is an HTTP PATCH request — a type of internet message that says "update specific fields on this record" (as opposed to replacing the whole record). It would target ServiceTitan's API at a URL constructed from the tenant ID and job ID.

Right now, the function checks `SERVICETITAN_ENABLED` first, returns immediately if it's `False`, and then hits `raise NotImplementedError` if somehow it's called with the switch on but the code unwritten.

---

### Pulling Data: `fetch_job_context()`

This function would do the reverse: given a ServiceTitan Job ID typed by the estimator, it would retrieve the job's details (job type, property type, cost breakdowns) and return them so the app can pre-fill the input form automatically.

The technical mechanism would be an HTTP GET request — a standard internet "fetch this record" message. Like the other functions, it returns `None` immediately when disabled, and the app falls back to requiring the estimator to type the values manually.

---

### Why Structure It This Way?

Writing disabled stub functions rather than nothing at all has a practical purpose: the rest of the app (`app.py`) can be written to call these functions right now without crashing, because the functions gracefully do nothing when disabled. When the integration is eventually built, the app's main logic doesn't need to change — only this file does.

---

## Takeaway

`servicetitan.py` is a reserved integration layer that is intentionally turned off. Its single boolean flag controls all behavior. When credentials become available, the three `TODO` blocks get implemented and the flag flips to `True` — nothing else in the app needs to change.
