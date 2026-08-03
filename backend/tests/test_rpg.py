"""Tests for RPG endpoints: quests, missions, rewards, characters, schedule, life areas."""

import pytest


# ---------------------------------------------------------------------------
# Quests
# ---------------------------------------------------------------------------
class TestQuests:
    def test_create_quest(self, client):
        resp = client.post("/api/quests", json={
            "user_id": 1,
            "title": "New Quest",
            "description": "A test quest",
            "xp_reward": 100,
            "status": "In progress",
            "category": "Study",
            "priority": "High",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["title"] == "New Quest"
        assert data["xp_reward"] == 100
        assert data["status"] == "In progress"
        assert data["category"] == "Study"

    def test_list_quests(self, client):
        resp = client.get("/api/quests")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_quests_by_status(self, client):
        resp = client.get("/api/quests?status=In progress")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert all(q["status"] == "In progress" for q in data)

    def test_list_quests_by_priority(self, client):
        resp = client.get("/api/quests?priority=High")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert all(q["priority"] == "High" for q in data)

    def test_list_quests_by_category(self, client):
        resp = client.get("/api/quests?category=Study")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_update_quest(self, client):
        resp = client.put("/api/quests/1", json={
            "user_id": 1,
            "title": "Updated Quest",
            "xp_reward": 300,
            "status": "Completed",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Quest"
        assert resp.json()["status"] == "Completed"

    def test_delete_quest(self, client):
        resp = client.delete("/api/quests/1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_complete_quest(self, client):
        # Quest id=2 "Fitness Challenge" has xp_reward=150, character starts at xp=1250
        resp = client.post("/api/quests/2/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Completed"

        # Verify character XP increased
        char_resp = client.get("/api/characters/1")
        assert char_resp.status_code == 200
        char = char_resp.json()
        assert char["xp"] == 1250 + 150  # 1400

    def test_complete_quest_triggers_level_up(self, client):
        # Set character to level=1, xp=800. Completing quest id=1 (xp_reward=200) gives 1000 XP -> level 2.
        client.put("/api/characters/1", json={
            "name": "Alex",
            "class_name": "Wizard",
            "level": 1,
            "xp": 800,
            "strength": 6,
            "agility": 5,
            "intelligence": 8,
            "endurance": 4,
            "current_quests": 2,
        })

        resp = client.post("/api/quests/1/complete")
        assert resp.status_code == 200

        char = client.get("/api/characters/1").json()
        assert char["xp"] == 1000
        assert char["level"] == 2  # (1000 // 1000) + 1 = 2, which is > 1


# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------
class TestMissions:
    def test_create_mission(self, client):
        resp = client.post("/api/missions", json={
            "user_id": 1,
            "title": "New Mission",
            "description": "A test mission",
            "mission_type": "Productivity",
            "priority": "High",
            "xp_reward": 250,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["title"] == "New Mission"

    def test_list_missions(self, client):
        resp = client.get("/api/missions")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_list_missions_by_status(self, client):
        resp = client.get("/api/missions?status=In Progress")
        assert resp.status_code == 200
        data = resp.json()
        assert all(m["status"] == "In Progress" for m in data)

    def test_list_missions_by_priority(self, client):
        resp = client.get("/api/missions?priority=High")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_update_mission(self, client):
        # Create a mission first, then update it
        created = client.post("/api/missions", json={
            "user_id": 1, "title": "Update Test", "xp_reward": 100,
        }).json()
        mid = created["id"]

        resp = client.put(f"/api/missions/{mid}", json={
            "title": "Updated Mission",
            "status": "Completed",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Mission"

    def test_delete_mission(self, client):
        created = client.post("/api/missions", json={
            "user_id": 1, "title": "Delete Test", "xp_reward": 100,
        }).json()
        mid = created["id"]

        resp = client.delete(f"/api/missions/{mid}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_complete_mission(self, client):
        created = client.post("/api/missions", json={
            "user_id": 1, "title": "Complete Test", "xp_reward": 300,
        }).json()
        mid = created["id"]

        resp = client.post(f"/api/missions/{mid}/complete")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Completed"

        char_resp = client.get("/api/characters/1")
        assert char_resp.status_code == 200
        char = char_resp.json()
        assert char["xp"] == 1250 + 300  # 1550

    def test_complete_mission_triggers_level_up(self, client):
        # Set char to level=1, xp=800
        client.put("/api/characters/1", json={
            "name": "Alex", "class_name": "Wizard", "level": 1, "xp": 800,
            "strength": 6, "agility": 5, "intelligence": 8, "endurance": 4,
        })

        created = client.post("/api/missions", json={
            "user_id": 1, "title": "Level Up Mission", "xp_reward": 200,
        }).json()
        mid = created["id"]

        resp = client.post(f"/api/missions/{mid}/complete")
        assert resp.status_code == 200

        char = client.get("/api/characters/1").json()
        assert char["xp"] == 1000
        assert char["level"] == 2


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------
class TestRewards:
    def test_list_rewards(self, client):
        resp = client.get("/api/rewards")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 4

    def test_list_rewards_available(self, client):
        resp = client.get("/api/rewards?available=true")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["is_available"] is True for r in data)

    def test_create_reward(self, client):
        resp = client.post("/api/rewards", json={
            "user_id": 1,
            "title": "New Reward",
            "description": "A test reward",
            "xp_cost": 100,
            "category": "Lifestyle",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["title"] == "New Reward"
        assert data["xp_cost"] == 100

    def test_update_reward(self, client):
        rewards = client.get("/api/rewards").json()
        if not rewards:
            client.post("/api/rewards", json={
                "user_id": 1, "title": "Test", "xp_cost": 50, "category": "Test",
            }).json()
            rewards = client.get("/api/rewards").json()
        rid = rewards[0]["id"]

        resp = client.put(f"/api/rewards/{rid}", json={
            "title": "Updated Reward",
            "xp_cost": 75,
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Reward"
        assert resp.json()["xp_cost"] == 75

    def test_delete_reward(self, client):
        created = client.post("/api/rewards", json={
            "user_id": 1, "title": "Delete Me", "xp_cost": 50, "category": "Test",
        }).json()
        rid = created["id"]

        resp = client.delete(f"/api/rewards/{rid}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_claim_reward(self, client):
        # Create a cheap reward
        created = client.post("/api/rewards", json={
            "user_id": 1, "title": "Cheap Treat", "xp_cost": 50, "category": "Test",
        }).json()
        rid = created["id"]

        resp = client.post(f"/api/rewards/{rid}/claim?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["reward_id"] == rid
        assert data["xp_cost"] == 50
        assert data["xp_remaining"] == 1250 - 50  # 1200
        assert data["claimed_at"] is not None

        # Verify no longer available
        reward = client.get(f"/api/rewards").json()
        claimed = [r for r in reward if r["id"] == rid]
        assert len(claimed) == 1
        assert claimed[0]["is_available"] is False
        assert claimed[0]["claimed_date"] is not None

    def test_claim_reward_enough_xp(self, client):
        created = client.post("/api/rewards", json={
            "user_id": 1, "title": "Affordable", "xp_cost": 200, "category": "Test",
        }).json()
        rid = created["id"]

        resp = client.post(f"/api/rewards/{rid}/claim?user_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["xp_remaining"] == 1250 - 200

    def test_claim_reward_not_enough_xp(self, client):
        # Set character XP too low
        client.put("/api/characters/1", json={
            "name": "Alex", "class_name": "Wizard", "level": 3, "xp": 10,
            "strength": 6, "agility": 5, "intelligence": 8, "endurance": 4,
        })

        created = client.post("/api/rewards", json={
            "user_id": 1, "title": "Too Expensive", "xp_cost": 500, "category": "Test",
        }).json()
        rid = created["id"]

        resp = client.post(f"/api/rewards/{rid}/claim?user_id=1")
        assert resp.status_code == 400
        assert "Not enough XP" in resp.json()["detail"]

    def test_claim_reward_already_claimed(self, client):
        created = client.post("/api/rewards", json={
            "user_id": 1, "title": "Claim Twice", "xp_cost": 50, "category": "Test",
        }).json()
        rid = created["id"]

        # Claim once
        client.post(f"/api/rewards/{rid}/claim?user_id=1")
        # Claim again
        resp = client.post(f"/api/rewards/{rid}/claim?user_id=1")
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Reward already claimed"

    def test_claim_reward_not_found(self, client):
        resp = client.post("/api/rewards/9999/claim?user_id=1")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Characters
# ---------------------------------------------------------------------------
class TestCharacters:
    def test_get_character(self, client):
        resp = client.get("/api/characters/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["user_id"] == 1
        assert data["name"] == "Alex"
        assert data["class_name"] == "Wizard"
        assert data["level"] == 3
        assert data["xp"] == 1250

    def test_get_character_not_found(self, client):
        resp = client.get("/api/characters/9999")
        assert resp.status_code == 404

    def test_add_xp_to_character(self, client):
        # Character starts at xp=1250, level=3
        resp = client.post("/api/characters/1/xp", json={"amount": 200})
        assert resp.status_code == 200
        data = resp.json()
        assert data["xp"] == 1250 + 200  # 1450
        assert data["level"] == 3  # (1450 // 1000) + 1 = 2, but 2 < 3, so level stays at 3

    def test_add_xp_triggers_level_up(self, client):
        # Set character to level=1, xp=0 so adding XP triggers level-up
        client.put("/api/characters/1", json={
            "name": "Alex",
            "class_name": "Wizard",
            "level": 1,
            "xp": 0,
            "strength": 6,
            "agility": 5,
            "intelligence": 8,
            "endurance": 4,
            "current_quests": 2,
        })

        resp = client.post("/api/characters/1/xp", json={"amount": 1500})
        assert resp.status_code == 200
        data = resp.json()
        assert data["xp"] == 1500
        assert data["level"] == 2  # (1500 // 1000) + 1 = 2, which is > 1

    def test_get_character_stats(self, client):
        resp = client.get("/api/characters/1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == 1

    def test_get_character_stats_not_found(self, client):
        resp = client.get("/api/characters/9999/stats")
        assert resp.status_code == 404

    def test_create_character(self, client):
        resp = client.post("/api/characters", json={
            "user_id": 2,
            "name": "Sam",
            "class_name": "Warrior",
            "level": 1,
            "xp": 0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Sam"
        assert data["class_name"] == "Warrior"

    def test_update_character(self, client):
        resp = client.put("/api/characters/1", json={
            "name": "Alex Updated",
            "level": 4,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "Alex Updated"
        assert resp.json()["level"] == 4

    def test_create_character_duplicate_user_id(self, client):
        # user_id=1 already has a character from seeding
        resp = client.post("/api/characters", json={
            "user_id": 1,
            "name": "Duplicate",
            "class_name": "Rogue",
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Schedule Events
# ---------------------------------------------------------------------------
class TestScheduleEvents:
    def test_list_schedule_events(self, client):
        resp = client.get("/api/schedule")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 5

    def test_list_schedule_events_by_day(self, client):
        resp = client.get("/api/schedule?day_of_week=0")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert all(e["day_of_week"] == 0 for e in data)

    def test_create_schedule_event(self, client):
        resp = client.post("/api/schedule", json={
            "user_id": 1,
            "title": "New Event",
            "day_of_week": 1,
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "color": "#ff0000",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["title"] == "New Event"
        assert data["day_of_week"] == 1

    def test_create_schedule_event_minimal(self, client):
        resp = client.post("/api/schedule", json={
            "user_id": 1,
            "title": "Minimal Event",
            "day_of_week": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Minimal Event"

    def test_update_schedule_event(self, client):
        # Create first
        created = client.post("/api/schedule", json={
            "user_id": 1, "title": "To Update", "day_of_week": 2,
        }).json()
        eid = created["id"]

        resp = client.put(f"/api/schedule/{eid}", json={
            "title": "Updated Event",
            "start_time": "08:00:00",
        })
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Event"

    def test_delete_schedule_event(self, client):
        created = client.post("/api/schedule", json={
            "user_id": 1, "title": "To Delete", "day_of_week": 4,
        }).json()
        eid = created["id"]

        resp = client.delete(f"/api/schedule/{eid}")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# Life Areas
# ---------------------------------------------------------------------------
class TestLifeAreas:
    def test_list_life_areas(self, client):
        resp = client.get("/api/life-areas")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_create_life_area(self, client):
        resp = client.post("/api/life-areas", json={
            "user_id": 1,
            "name": "Career",
            "satisfaction_score": 5,
            "goal": "Get promoted",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] is not None
        assert data["name"] == "Career"

    def test_update_life_area(self, client):
        resp = client.put("/api/life-areas/1", json={
            "name": "Academics Updated",
            "satisfaction_score": 9,
        })
        assert resp.status_code == 200
        assert resp.json()["satisfaction_score"] == 9
        assert resp.json()["name"] == "Academics Updated"

    def test_delete_life_area(self, client):
        resp = client.delete("/api/life-areas/1")
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_update_life_area_not_found(self, client):
        resp = client.put("/api/life-areas/9999", json={"name": "Ghost"})
        assert resp.status_code == 404