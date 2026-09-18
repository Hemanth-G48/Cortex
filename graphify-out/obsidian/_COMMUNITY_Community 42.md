---
type: community
cohesion: 0.09
members: 54
---

# Community 42

**Cohesion:** 0.09 - loosely connected
**Members:** 54 nodes

## Members
- [[Auth router signup, login (legacy + credential), me, logout.]] - rationale - backend/app/routers/auth.py
- [[BaseModel_63]] - code
- [[Bind the owner to an institutionprogram (SyllabusAI enrollment).]] - rationale - backend/app/routers/profile.py
- [[Clear all tracked failure state (used by tests and ops tooling).]] - rationale - backend/app/routers/auth.py
- [[EnrollmentUpdate]] - code - backend/app/schemas/user.py
- [[HTTPAuthorizationCredentials]] - code
- [[Profile router — the single owner's profile (no loginauth).  Replaces the old `]] - rationale - backend/app/routers/profile.py
- [[Raise 429 when the client has exhausted its failure budget.]] - rationale - backend/app/routers/auth.py
- [[Request]] - code
- [[Request_2]] - code
- [[Session_3]] - code
- [[Session_5]] - code
- [[Session_85]] - code
- [[Test-only auth shim (mounted only under pytest).  Production is single-user and]] - rationale - backend/app/routers/auth_test.py
- [[Test-only resolve the user from a valid bearer token.]] - rationale - backend/app/routers/auth_test.py
- [[User_3]] - code
- [[User_4]] - code
- [[User_63]] - code
- [[UserBase]] - code - backend/app/schemas/user.py
- [[UserCreate]] - code - backend/app/schemas/user.py
- [[UserLogin]] - code - backend/app/schemas/user.py
- [[UserResponse]] - code - backend/app/schemas/user.py
- [[UserSignup]] - code - backend/app/schemas/user.py
- [[UserUpdate]] - code - backend/app/schemas/user.py
- [[_check_login_lockout()]] - code - backend/app/routers/auth.py
- [[_check_login_lockout()_1]] - code - backend/app/routers/auth_test.py
- [[_client_ip()]] - code - backend/app/routers/auth.py
- [[_client_ip()_1]] - code - backend/app/routers/auth_test.py
- [[_current()]] - code - backend/app/routers/auth_test.py
- [[_prune_failures()]] - code - backend/app/routers/auth.py
- [[_prune_failures()_1]] - code - backend/app/routers/auth_test.py
- [[_record_login_failure()]] - code - backend/app/routers/auth.py
- [[_record_login_failure()_1]] - code - backend/app/routers/auth_test.py
- [[_reset_login_failures()]] - code - backend/app/routers/auth_test.py
- [[auth.py]] - code - backend/app/routers/auth.py
- [[auth_test.py]] - code - backend/app/routers/auth_test.py
- [[create_bearer_token()]] - code - backend/app/services/security.py
- [[get_profile()_1]] - code - backend/app/routers/profile.py
- [[hash_password()]] - code - backend/app/services/security.py
- [[login()]] - code - backend/app/routers/auth.py
- [[login()_1]] - code - backend/app/routers/auth_test.py
- [[logout()]] - code - backend/app/routers/auth.py
- [[logout()_1]] - code - backend/app/routers/auth_test.py
- [[me()]] - code - backend/app/routers/auth.py
- [[me()_1]] - code - backend/app/routers/auth_test.py
- [[profile.py]] - code - backend/app/routers/profile.py
- [[reset_login_failures()]] - code - backend/app/routers/auth.py
- [[schemasuser.py]] - code - backend/app/schemas/user.py
- [[signup()]] - code - backend/app/routers/auth.py
- [[signup()_1]] - code - backend/app/routers/auth_test.py
- [[update_enrollment()]] - code - backend/app/routers/auth.py
- [[update_enrollment()_1]] - code - backend/app/routers/profile.py
- [[update_profile()]] - code - backend/app/routers/profile.py
- [[verify_password()]] - code - backend/app/services/security.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_42
SORT file.name ASC
```

## Connections to other communities
- 25 edges to [[_COMMUNITY_Community 5]]
- 8 edges to [[_COMMUNITY_Community 69]]
- 8 edges to [[_COMMUNITY_Community 144]]
- 7 edges to [[_COMMUNITY_Community 7]]
- 5 edges to [[_COMMUNITY_Community 47]]
- 3 edges to [[_COMMUNITY_Community 10]]
- 3 edges to [[_COMMUNITY_Community 267]]
- 2 edges to [[_COMMUNITY_Community 1]]
- 2 edges to [[_COMMUNITY_Community 94]]
- 1 edge to [[_COMMUNITY_Community 157]]
- 1 edge to [[_COMMUNITY_Community 295]]
- 1 edge to [[_COMMUNITY_Community 122]]
- 1 edge to [[_COMMUNITY_Community 166]]

## Top bridge nodes
- [[create_bearer_token()]] - degree 15, connects to 6 communities
- [[auth.py]] - degree 30, connects to 5 communities
- [[auth_test.py]] - degree 29, connects to 5 communities
- [[profile.py]] - degree 19, connects to 3 communities
- [[UserResponse]] - degree 17, connects to 2 communities