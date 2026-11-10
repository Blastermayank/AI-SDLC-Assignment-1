# Live Gemini verification record - 2026-11-10

Task T059 / SC-004 (FR-020). Recorded automatically by a Playwright driver that used the real
Part 1B page in Microsoft Edge against the portal started with `start.ps1 -NoBrowser`
(http://127.0.0.1:8000). Each snippet was submitted once, 6 s apart, with no retries. Rows are the
observed results, unedited. Model output varies between calls by design.

- Portal commit: `f2d3c75`
- Model reported by the portal: gemini-3.5-flash-lite
- Submissions: 10; completed analyses: 9
- Every submission ended within 60 s (click to final status): yes
- Completed analyses whose findings were all displayed: 9 of 10
- SC-004 (all within 60 s and at least 9 of 10 displayed): met

| # | UTC time | Input | Chars | Outcome | HTTP | Server s | Wall s | Findings | Layer 1 | Layer 2 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-10T18:30:08Z | built-in sample 'sql' | 149 | completed | 200 | 8.7 | 14.1 | SQL Injection (High) | PASS | PASS |
| 2 | 2026-11-10T18:30:29Z | built-in sample 'command' | 114 | completed | 200 | 1.8 | 2.0 | Command Injection (High) | PASS | PASS |
| 3 | 2026-11-10T18:30:37Z | built-in sample 'credential' | 108 | completed | 200 | 1.4 | 1.5 | Hardcoded Credentials (High) | PASS | PASS |
| 4 | 2026-11-10T18:30:44Z | built-in sample 'benign' | 95 | completed | 200 | 6.8 | 6.8 | 0 | PASS | PASS |
| 5 | 2026-11-10T18:30:57Z | pasted: insecure deserialisation (Python) | 85 | service_error | 502 |  | 1.0 | - | - | - |
| 6 | 2026-11-10T18:31:04Z | pasted: eval code injection (Python) | 117 | completed | 200 | 2.2 | 2.2 | Remote Code Execution (High) | PASS | PASS |
| 7 | 2026-11-10T18:31:12Z | pasted: path traversal (Python) | 140 | completed | 200 | 1.5 | 1.6 | 0 | PASS | PASS |
| 8 | 2026-11-10T18:31:20Z | pasted: cross-site scripting (JavaScript) | 136 | completed | 200 | 6.0 | 6.1 | Cross-Site Scripting (XSS) (High) | PASS | PASS |
| 9 | 2026-11-10T18:31:32Z | pasted: weak password hashing (Python) | 100 | completed | 200 | 2.1 | 2.1 | Weak Cryptography (High) | PASS | PASS |
| 10 | 2026-11-10T18:31:40Z | pasted: server-side request forgery (Python) | 86 | completed | 200 | 1.6 | 1.6 | 0 | PASS | PASS |

## Per-submission detail

### 1. built-in sample 'sql'

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 8.7 s · 1 finding"
- Finding cards shown: 1
- Raw model output:

````json
{"status": "success", "findings": [{"vulnerability": "SQL Injection", "severity": "High", "description": "The function dynamically formats a SQL query string using untrusted input from the username parameter, allowing an attacker to manipulate the query structure.", "evidence": "query = f\"SELECT * FROM users WHERE name = '{username}'\"", "remediation": "Use parameterized queries by passing the parameters as a tuple to the execute method, such as conn.execute(\"SELECT * FROM users WHERE name = ?\", (username,))"}]}
````

### 2. built-in sample 'command'

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 1.8 s · 1 finding"
- Finding cards shown: 1
- Raw model output:

````json
{"status": "success", "findings": [{"vulnerability": "Command Injection", "severity": "High", "description": "The function concatenates untrusted input directly into a shell command string while shell=True is enabled, allowing arbitrary command execution.", "evidence": "return subprocess.run(\"ping -c 1 \" + host, shell=True, capture_output=True)", "remediation": "Avoid using shell=True and pass the command and arguments as a list of strings, or validate and sanitize the host input thoroughly."}]}
````

### 3. built-in sample 'credential'

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 1.4 s · 1 finding"
- Finding cards shown: 1
- Raw model output:

````json
{"status": "success", "findings": [{"vulnerability": "Hardcoded Credentials", "severity": "High", "description": "A sensitive password string is hardcoded directly into the source code.", "evidence": "DB_PASSWORD = \"Pr0d-Admin-2026!\"", "remediation": "Store sensitive credentials securely using environment variables or a secret management service rather than hardcoding them in the source code."}]}
````

### 4. built-in sample 'benign'

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 6.8 s · 0 findings"
- Finding cards shown: 0
- Raw model output:

````json
{"status": "success", "findings": []}
````

### 5. pasted: insecure deserialisation (Python)

- Status line shown on the page: "service error The Gemini service returned an error (for example, high demand). No analysis was made; try again later."
- Error message: The Gemini service returned an error. Try again later.

### 6. pasted: eval code injection (Python)

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 2.2 s · 1 finding"
- Finding cards shown: 1
- Raw model output:

````json
{"status": "success", "findings": [{"vulnerability": "Remote Code Execution", "severity": "High", "description": "The application uses the built-in eval() function to execute an expression that originates directly from a request query string. This allows an attacker to inject and execute arbitrary Python code.", "evidence": "return eval(expression)", "remediation": "Avoid using eval() for untrusted input. Instead, use a safe parser or explicitly parse and validate the expression components."}]}
````

### 7. pasted: path traversal (Python)

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 1.5 s · 0 findings"
- Finding cards shown: 0
- Raw model output:

````json
{"status": "success", "findings": []}
````

### 8. pasted: cross-site scripting (JavaScript)

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 6.0 s · 1 finding"
- Finding cards shown: 1
- Raw model output:

````json
{"status": "success", "findings": [{"vulnerability": "Cross-Site Scripting (XSS)", "severity": "High", "description": "User-supplied input retrieved from URL parameters is directly concatenated into HTML and assigned to innerHTML, allowing potential execution of arbitrary JavaScript.", "evidence": "document.getElementById('greeting').innerHTML = 'Hello ' + name;", "remediation": "Use textContent instead of innerHTML or properly sanitize the user input before inserting it into the DOM."}]}
````

### 9. pasted: weak password hashing (Python)

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 2.1 s · 1 finding"
- Finding cards shown: 1
- Raw model output:

````json
{"status": "success", "findings": [{"vulnerability": "Weak Cryptography", "severity": "High", "description": "The code uses MD5, a cryptographically broken and insecure hash function, to hash passwords.", "evidence": "return hashlib.md5(password.encode()).hexdigest()", "remediation": "Use a strong, modern password hashing algorithm such as bcrypt, Argon2, or PBKDF2 instead of MD5."}]}
````

### 10. pasted: server-side request forgery (Python)

- Status line shown on the page: "Completed Analysis completed by gemini-3.5-flash-lite in 1.6 s · 0 findings"
- Finding cards shown: 0
- Raw model output:

````json
{"status": "success", "findings": []}
````
