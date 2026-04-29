import argparse

from app.backend.repositories.users import replace_user_clubs, upsert_app_user


def parse_args():
    parser = argparse.ArgumentParser(description="Create or update an app user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default=None)
    parser.add_argument("--role", choices=["viewer", "club_rep", "admin"], default="club_rep")
    parser.add_argument("--club-id", type=int, action="append", default=[])
    parser.add_argument("--inactive", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    user = upsert_app_user(
        email=args.email,
        full_name=args.name,
        role=args.role,
        is_active=not args.inactive,
    )
    replace_user_clubs(user["id"], args.club_id)
    print(
        f"Saved app user {user['email']} with role={user['role']} "
        f"active={user['is_active']} clubs={sorted(set(args.club_id))}"
    )


if __name__ == "__main__":
    main()
