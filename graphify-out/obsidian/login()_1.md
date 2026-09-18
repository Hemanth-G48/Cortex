---
source_file: "backend/app/routers/auth_test.py"
type: "code"
community: "Community 42"
location: "L133"
tags:
  - graphify/code
  - graphify/EXTRACTED
  - community/Community_42
---

# login()

## Connections
- [[Request_2]] - `references` [EXTRACTED]
- [[Session_5]] - `references` [EXTRACTED]
- [[User]] - `indirect_call` [INFERRED]
- [[UserLogin]] - `calls` [EXTRACTED]
- [[UserResponse]] - `references` [EXTRACTED]
- [[_check_login_lockout()_1]] - `calls` [EXTRACTED]
- [[_client_ip()_1]] - `calls` [EXTRACTED]
- [[_record_login_failure()_1]] - `calls` [EXTRACTED]
- [[_reset_login_failures()]] - `calls` [EXTRACTED]
- [[auth_test.py]] - `contains` [EXTRACTED]
- [[create_bearer_token()]] - `calls` [EXTRACTED]
- [[verify_password()]] - `calls` [EXTRACTED]

#graphify/code #graphify/EXTRACTED #community/Community_42