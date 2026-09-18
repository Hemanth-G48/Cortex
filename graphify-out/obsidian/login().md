---
source_file: "backend/app/routers/auth.py"
type: "code"
community: "Community 42"
location: "L127"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_42
---

# login()

## Connections
- [[Request]] - `references` [EXTRACTED]
- [[Session_3]] - `references` [EXTRACTED]
- [[User]] - `indirect_call` [INFERRED]
- [[UserLogin]] - `calls` [EXTRACTED]
- [[UserResponse]] - `references` [EXTRACTED]
- [[_check_login_lockout()]] - `calls` [EXTRACTED]
- [[_client_ip()]] - `calls` [EXTRACTED]
- [[_record_login_failure()]] - `calls` [EXTRACTED]
- [[_reset_login_failures()]] - `calls` [INFERRED]
- [[auth.py]] - `contains` [EXTRACTED]
- [[create_bearer_token()]] - `calls` [EXTRACTED]
- [[verify_password()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_42