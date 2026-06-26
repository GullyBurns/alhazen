#!/usr/bin/env python3
"""
agent-os CLI -- large-scale operator context dataset.

Builds a structured personal context graph in TypeDB from connected services
(Gmail, Calendar, GitHub, LinkedIn, Drive, HealthKit) and manual entry.

Usage:
    python skills/agent-os/agent_os.py <command> [options]

Profile commands:
    create-profile     Create aos-operator-profile for a person (idempotent)
    show-profile       Show full structured profile for a person
    show-ingestion     Show last ingestion timestamps per source

Manual entry commands:
    add-goal           Add a goal linked to the operator profile
    add-preference     Add a preference or constraint
    add-life-event     Add a career/personal milestone
    add-topic          Add a topic/interest area
    update-narrative   Set or replace the full-text content on any profile entity

Context retrieval:
    get-context        Get structured context JSON (all or one dimension)
                       Use --with-content to include full narratives

Environment:
    TYPEDB_HOST       TypeDB server host (default: localhost)
    TYPEDB_PORT       TypeDB server port (default: 1729)
    TYPEDB_DATABASE   Database name (default: alhazen_notebook)
    TYPEDB_USERNAME   TypeDB username (default: admin)
    TYPEDB_PASSWORD   TypeDB password (default: password)
"""

import argparse
import json
import os
import sys

try:
    from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB
    TYPEDB_AVAILABLE = True
except ImportError:
    TYPEDB_AVAILABLE = False
    print("Warning: typedb-driver not installed. pip install 'typedb-driver>=3.8.0'", file=sys.stderr)

try:
    _SKILL_DIR = os.path.dirname(os.path.realpath(__file__))
    _PROJECT_ROOT = os.path.abspath(os.path.join(_SKILL_DIR, "..", ".."))
    sys.path.insert(0, _PROJECT_ROOT)
    from src.skillful_alhazen.utils.skill_helpers import escape_string, generate_id, get_timestamp
except ImportError:
    import uuid
    from datetime import datetime, timezone

    def escape_string(s: str) -> str:
        if s is None:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

    def generate_id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    def get_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alh_core")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")


def get_driver():
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


def _find_profile(driver, person_id: str) -> str | None:
    """Return the aos-operator-profile ID for a person, or None."""
    pid = escape_string(person_id)
    with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
        results = list(tx.query(f'''
            match
              $person isa alh-person, has id "{pid}";
              (bearer: $person, borne-role: $profile) isa alh-role-bearing;
              $profile isa aos-operator-profile, has id $pid;
            fetch {{ "id": $pid }};
        ''').resolve())
    if not results:
        return None
    return results[0]["id"]


def _get_profile_id_or_exit(person_id: str) -> str:
    """Find profile ID or print error and exit."""
    with get_driver() as driver:
        profile_id = _find_profile(driver, person_id)
    if not profile_id:
        print(json.dumps({
            "success": False,
            "error": f"No aos-operator-profile found for person '{person_id}'. Run create-profile first."
        }))
        sys.exit(1)
    return profile_id


def _insert_content(driver, entity_id: str, narrative: str) -> None:
    """
    Set or replace the content attribute on an entity.
    Deletes any existing content value first, then inserts the new one.
    """
    eid = escape_string(entity_id)
    # Delete existing content if present (no-op if absent -- match fails silently via two-tx pattern)
    try:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            results = list(tx.query(f'''
                match $e isa alh-domain-thing, has id "{eid}", has content $old;
                fetch {{ "has_content": $old }};
            ''').resolve())
            if results:
                tx.query(f'''
                    match $e isa alh-domain-thing, has id "{eid}", has content $old;
                    delete has $old of $e;
                ''').resolve()
            tx.commit()
    except Exception:
        pass  # entity had no content -- that's fine

    # Insert new content
    escaped = escape_string(narrative)
    with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
        tx.query(f'''
            match $e isa alh-domain-thing, has id "{eid}";
            insert $e has content "{escaped}";
        ''').resolve()
        tx.commit()


def cmd_create_profile(args):
    """Create aos-operator-profile for a person (idempotent)."""
    pid = escape_string(args.person)
    ts = get_timestamp()

    with get_driver() as driver:
        existing = _find_profile(driver, args.person)
        if existing:
            print(json.dumps({"success": True, "profile_id": existing, "created": False}))
            return

        profile_id = generate_id("aos-profile")
        profile_q = f'''
        insert $profile isa aos-operator-profile,
            has id "{profile_id}",
            has name "{pid} (agent-os profile)",
            has alh-role-status "active",
            has created-at {ts};
        '''
        bearing_q = f'''
        match
          $person isa alh-person, has id "{pid}";
          $profile isa aos-operator-profile, has id "{profile_id}";
        insert (bearer: $person, borne-role: $profile) isa alh-role-bearing;
        '''

        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(profile_q).resolve()
            tx.commit()
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(bearing_q).resolve()
            tx.commit()

    print(json.dumps({"success": True, "profile_id": profile_id, "created": True}))


def cmd_add_goal(args):
    """Add an aos-goal linked to the operator's profile."""
    ts = get_timestamp()
    profile_id = _get_profile_id_or_exit(args.person)
    gid = generate_id("aos-goal")
    desc = escape_string(args.description)
    priority = args.priority

    q = f'''
    match $profile isa aos-operator-profile, has id "{escape_string(profile_id)}";
    insert
      $goal isa aos-goal,
        has id "{gid}",
        has description "{desc}",
        has aos-priority {priority},
        has aos-goal-status "active",
        has created-at {ts}'''
    if args.target_date:
        q += f',\n        has aos-target-date {args.target_date}'
    q += ';\n      (profile: $profile, goal: $goal) isa aos-profile-has-goal;'

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(q).resolve()
            tx.commit()
        if args.narrative:
            _insert_content(driver, gid, args.narrative)

    print(json.dumps({"success": True, "id": gid}))


def cmd_add_preference(args):
    """Add an aos-preference linked to the operator's profile."""
    ts = get_timestamp()
    profile_id = _get_profile_id_or_exit(args.person)
    pid = generate_id("aos-pref")
    desc = escape_string(args.description)
    cat = escape_string(args.category)
    strength = escape_string(args.strength)

    q = f'''
    match $profile isa aos-operator-profile, has id "{escape_string(profile_id)}";
    insert
      $pref isa aos-preference,
        has id "{pid}",
        has description "{desc}",
        has aos-preference-category "{cat}",
        has aos-preference-strength "{strength}",
        has created-at {ts};
      (profile: $profile, preference: $pref) isa aos-profile-has-preference;
    '''

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(q).resolve()
            tx.commit()
        if args.narrative:
            _insert_content(driver, pid, args.narrative)

    print(json.dumps({"success": True, "id": pid}))


def cmd_add_life_event(args):
    """Add an aos-life-event linked to the operator's profile."""
    ts = get_timestamp()
    profile_id = _get_profile_id_or_exit(args.person)
    eid = generate_id("aos-event")
    desc = escape_string(args.description)
    event_type = escape_string(args.type)
    event_date = args.date

    q = f'''
    match $profile isa aos-operator-profile, has id "{escape_string(profile_id)}";
    insert
      $event isa aos-life-event,
        has id "{eid}",
        has description "{desc}",
        has aos-event-type "{event_type}",
        has aos-event-date {event_date},
        has created-at {ts};
      (profile: $profile, event: $event) isa aos-profile-has-life-event;
    '''

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(q).resolve()
            tx.commit()
        if args.narrative:
            _insert_content(driver, eid, args.narrative)

    print(json.dumps({"success": True, "id": eid}))


def cmd_add_topic(args):
    """Add an aos-topic (global -- discovered from interactions or manually added)."""
    _get_profile_id_or_exit(args.person)  # validate profile exists
    ts = get_timestamp()
    tid = generate_id("aos-topic")
    name = escape_string(args.name)
    desc = escape_string(args.description or "")
    importance = escape_string(args.importance)

    q = f'''
    insert $topic isa aos-topic,
        has id "{tid}",
        has name "{name}",
        has aos-importance "{importance}",
        has created-at {ts}'''
    if desc:
        q += f',\n        has description "{desc}"'
    q += ";"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(q).resolve()
            tx.commit()
        if args.narrative:
            _insert_content(driver, tid, args.narrative)

    print(json.dumps({"success": True, "id": tid}))


def cmd_update_narrative(args):
    """Set or replace the full-text content on any profile entity by ID."""
    with get_driver() as driver:
        # Verify entity exists
        eid = escape_string(args.entity_id)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $e isa alh-domain-thing, has id "{eid}";
                fetch {{ "id": $e.id }};
            ''').resolve())
        if not results:
            print(json.dumps({"success": False, "error": f"No entity found with id '{args.entity_id}'"}))
            sys.exit(1)

        _insert_content(driver, args.entity_id, args.narrative)

    print(json.dumps({"success": True, "id": args.entity_id}))


def _fetch_optional_content(driver, entity_id: str) -> str | None:
    """Return the content string for an entity, or None if not set."""
    eid = escape_string(entity_id)
    try:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(f'''
                match $e isa alh-domain-thing, has id "{eid}", has content $c;
                fetch {{ "content": $c }};
            ''').resolve())
        return results[0]["content"] if results else None
    except Exception:
        return None


def cmd_get_context(args):
    """Return structured context JSON for a person."""
    dimension = args.dimension or "all"
    with_content = getattr(args, "with_content", False)

    with get_driver() as driver:
        profile_id = _find_profile(driver, args.person)
        if not profile_id:
            print(json.dumps({"success": False, "error": f"No profile for person '{args.person}'"}))
            return
        pesc = escape_string(profile_id)

        result = {"success": True}

        if dimension in ("goals", "all"):
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rows = list(tx.query(f'''
                    match
                      $profile isa aos-operator-profile, has id "{pesc}";
                      (profile: $profile, goal: $goal) isa aos-profile-has-goal;
                      $goal has id $gid, has description $desc,
                            has aos-priority $pri, has aos-goal-status $status;
                    fetch {{
                      "id": $gid, "description": $desc,
                      "priority": $pri, "status": $status
                    }};
                ''').resolve())
            goals = [
                {"id": r["id"], "description": r["description"],
                 "priority": r["priority"], "status": r["status"]}
                for r in rows
            ]
            if with_content:
                for item in goals:
                    item["content"] = _fetch_optional_content(driver, item["id"])
            result["goals"] = goals

        if dimension in ("preferences", "all"):
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rows = list(tx.query(f'''
                    match
                      $profile isa aos-operator-profile, has id "{pesc}";
                      (profile: $profile, preference: $pref) isa aos-profile-has-preference;
                      $pref has id $pid, has description $desc,
                            has aos-preference-category $cat,
                            has aos-preference-strength $str;
                    fetch {{
                      "id": $pid, "description": $desc,
                      "category": $cat, "strength": $str
                    }};
                ''').resolve())
            prefs = [
                {"id": r["id"], "description": r["description"],
                 "category": r["category"], "strength": r["strength"]}
                for r in rows
            ]
            if with_content:
                for item in prefs:
                    item["content"] = _fetch_optional_content(driver, item["id"])
            result["preferences"] = prefs

        if dimension in ("career", "all"):
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rows = list(tx.query(f'''
                    match
                      $profile isa aos-operator-profile, has id "{pesc}";
                      (profile: $profile, event: $event) isa aos-profile-has-life-event;
                      $event has id $eid, has description $desc,
                              has aos-event-type $etype, has aos-event-date $edate;
                    fetch {{
                      "id": $eid, "description": $desc,
                      "type": $etype, "date": $edate
                    }};
                ''').resolve())
            events = [
                {"id": r["id"], "description": r["description"],
                 "type": r["type"], "date": str(r["date"])}
                for r in rows
            ]
            if with_content:
                for item in events:
                    item["content"] = _fetch_optional_content(driver, item["id"])
            result["life_events"] = events

        if dimension in ("topics", "all"):
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rows = list(tx.query(f'''
                    match $topic isa aos-topic,
                          has id $tid, has name $tname, has aos-importance $imp;
                    fetch {{ "id": $tid, "name": $tname, "importance": $imp }};
                ''').resolve())
            topics = [
                {"id": r["id"], "name": r["name"], "importance": r["importance"]}
                for r in rows
            ]
            if with_content:
                for item in topics:
                    item["content"] = _fetch_optional_content(driver, item["id"])
            result["topics"] = topics

        if dimension in ("interactions", "all"):
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rows = list(tx.query(f'''
                    match $i isa alh-interaction, has id $iid, has alh-interaction-type $itype;
                    fetch {{ "id": $iid, "type": $itype }};
                ''').resolve())
            result["interactions"] = [
                {"id": r["id"], "type": r["type"]}
                for r in rows
            ]

        if dimension in ("health", "all"):
            with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
                rows = list(tx.query(f'''
                    match $h isa aos-health-snapshot,
                          has aos-metric-type $mtype, has aos-metric-value $mval,
                          has aos-metric-date $mdate;
                    fetch {{ "metric_type": $mtype, "value": $mval, "date": $mdate }};
                ''').resolve())
            result["health"] = [
                {"metric_type": r["metric_type"],
                 "value": r["value"],
                 "date": str(r["date"])}
                for r in rows
            ]

    print(json.dumps(result))


def cmd_show_profile(args):
    """Show full structured profile for a person."""
    pid = escape_string(args.person)

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            rows = list(tx.query(f'''
                match $p isa alh-person, has id "{pid}", has name $n;
                fetch {{ "id": $p.id, "name": $n }};
            ''').resolve())
        if not rows:
            print(json.dumps({"success": False, "error": f"Person '{args.person}' not found"}))
            return
        person = {"id": rows[0]["id"], "name": rows[0]["name"]}

        profile_id = _find_profile(driver, args.person)

    print(json.dumps({
        "success": True,
        "person": person,
        "profile_id": profile_id,
    }))


def cmd_show_ingestion(args):
    """Show last ingestion note per source for a person's profile."""
    with get_driver() as driver:
        profile_id = _find_profile(driver, args.person)
        if not profile_id:
            print(json.dumps({"success": False, "error": f"No profile for '{args.person}'"}))
            return
        pesc = escape_string(profile_id)

        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            rows = list(tx.query(f'''
                match
                  $profile isa aos-operator-profile, has id "{pesc}";
                  (subject: $profile, note: $note) isa alh-aboutness;
                  $note isa aos-ingestion-note,
                        has aos-ingestion-source $src,
                        has aos-items-processed $count,
                        has created-at $ts;
                fetch {{
                  "source": $src, "items": $count, "last_run": $ts
                }};
            ''').resolve())
        ingestion = [
            {"source": r["source"],
             "items": r["items"],
             "last_run": str(r["last_run"])}
            for r in rows
        ]

    print(json.dumps({"success": True, "ingestion": ingestion}))


# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(
        prog="agent-os",
        description="agent-os: large-scale operator context dataset",
    )
    sub = parser.add_subparsers(dest="command")

    # create-profile
    p = sub.add_parser("create-profile", help="Create aos-operator-profile for a person (idempotent)")
    p.add_argument("--person", required=True, help="alh-person ID")

    # add-goal
    p = sub.add_parser("add-goal", help="Add a goal linked to the operator profile")
    p.add_argument("--person", required=True)
    p.add_argument("--description", required=True,
                   help="One-line summary of the goal")
    p.add_argument("--narrative",
                   help="Full rich-text narrative: rationale, success criteria, constraints, backstory")
    p.add_argument("--priority", type=int, required=True, choices=[1, 2, 3, 4, 5])
    p.add_argument("--target-date", help="ISO datetime e.g. 2026-12-31T00:00:00")

    # add-preference
    p = sub.add_parser("add-preference", help="Add a preference or constraint")
    p.add_argument("--person", required=True)
    p.add_argument("--category", required=True,
                   choices=["work-style", "technical", "communication", "personal"])
    p.add_argument("--description", required=True,
                   help="One-line summary of the preference")
    p.add_argument("--narrative",
                   help="Full rich-text narrative: stories of when violated, why it matters, "
                        "how to probe for it in interviews")
    p.add_argument("--strength", required=True, choices=["hard", "soft"])

    # add-life-event
    p = sub.add_parser("add-life-event", help="Add a career/personal milestone")
    p.add_argument("--person", required=True)
    p.add_argument("--type", required=True,
                   choices=["job-start", "job-end", "publication", "conference",
                            "project-launch", "education-start", "education-end", "award"])
    p.add_argument("--date", required=True, help="ISO datetime e.g. 2020-01-15T00:00:00")
    p.add_argument("--description", required=True,
                   help="One-line summary of the event")
    p.add_argument("--narrative",
                   help="Full rich-text narrative: what happened, what was built, "
                        "what was learned, why it ended, lasting impact")

    # add-topic
    p = sub.add_parser("add-topic", help="Add a topic/interest area")
    p.add_argument("--person", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description",
                   help="One-line summary of the topic area")
    p.add_argument("--narrative",
                   help="Full rich-text narrative: depth of expertise, notable projects, "
                        "how it was acquired, where it is heading")
    p.add_argument("--importance", default="medium", choices=["high", "medium", "low"])

    # update-narrative
    p = sub.add_parser("update-narrative",
                       help="Set or replace the full-text content on any profile entity")
    p.add_argument("--entity-id", required=True,
                   help="The id of the entity to update (e.g. aos-goal-abc123)")
    p.add_argument("--narrative", required=True,
                   help="Full rich-text content to store")

    # get-context
    p = sub.add_parser("get-context", help="Get structured context JSON")
    p.add_argument("--person", required=True)
    p.add_argument("--dimension",
                   choices=["goals", "preferences", "career", "topics", "interactions", "health", "all"],
                   default="all")
    p.add_argument("--with-content", action="store_true",
                   help="Include full narrative content for each item")

    # show-profile
    p = sub.add_parser("show-profile", help="Show full structured profile")
    p.add_argument("--person", required=True)

    # show-ingestion
    p = sub.add_parser("show-ingestion", help="Show last ingestion timestamps per source")
    p.add_argument("--person", required=True)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "create-profile":   cmd_create_profile,
        "add-goal":         cmd_add_goal,
        "add-preference":   cmd_add_preference,
        "add-life-event":   cmd_add_life_event,
        "add-topic":        cmd_add_topic,
        "update-narrative": cmd_update_narrative,
        "get-context":      cmd_get_context,
        "show-profile":     cmd_show_profile,
        "show-ingestion":   cmd_show_ingestion,
    }

    fn = dispatch.get(args.command)
    if fn is None:
        print(json.dumps({"success": False, "error": f"Unknown command: {args.command}"}))
        sys.exit(1)

    fn(args)


if __name__ == "__main__":
    main()
