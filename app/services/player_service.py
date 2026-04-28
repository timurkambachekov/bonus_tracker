from dataclasses import asdict

from app.domain import Competition, Contract
from app.services.bonus_logic import build_bonus_model, build_stats_snapshot, evaluate_bonus_progress


def serialize_player(row):
    competition = None
    if row.get("competition_id") and row.get("competition_name"):
        competition = asdict(
            Competition(
                id=row["competition_id"],
                name=row["competition_name"],
                code=row.get("competition_code"),
                country=row.get("competition_country"),
                season=row.get("competition_season"),
            )
        )

    return {
        "id": row["id"],
        "transfermarkt_player_id": row.get("transfermarkt_player_id"),
        "player_name": row.get("player_name") or "Unknown player",
        "position": row.get("position"),
        "date_of_birth": str(row.get("date_of_birth")) if row.get("date_of_birth") else None,
        "nationality": row.get("nationality"),
        "height_m": float(row["height_m"]) if row.get("height_m") is not None else None,
        "foot": row.get("foot"),
        "market_value_eur": float(row["market_value_eur"])
        if row.get("market_value_eur") is not None
        else None,
        "club_id": row.get("club_id"),
        "club_slug": row.get("club_slug"),
        "club_name": row.get("club_name"),
        "competition": competition,
    }


def attach_bonus_conditions(bonuses, conditions):
    conditions_by_bonus = {}
    for condition in conditions:
        conditions_by_bonus.setdefault(condition["contract_bonus_id"], []).append(condition)

    items = []
    for bonus in bonuses:
        item = dict(bonus)
        item["conditions"] = conditions_by_bonus.get(bonus["id"], [])
        items.append(item)
    return items


def build_contract_list(contracts, bonuses, conditions, latest_stats=None, include_progress=True):
    bonuses_by_contract = {}
    for bonus in attach_bonus_conditions(bonuses, conditions):
        bonuses_by_contract.setdefault(bonus["contract_id"], []).append(bonus)

    stats_snapshot = build_stats_snapshot(latest_stats) if latest_stats else None
    items = []

    for contract in contracts:
        contract_bonuses = bonuses_by_contract.get(contract["id"], [])
        domain_bonuses = [build_bonus_model(bonus) for bonus in contract_bonuses]
        domain_bonuses_by_id = {bonus.id: bonus for bonus in domain_bonuses}
        binding_groups = {}

        for bonus in contract_bonuses:
            group_name = bonus.get("binding_group")
            if group_name:
                binding_groups.setdefault(group_name, []).append(domain_bonuses_by_id[bonus["id"]])

        contract_model = Contract(
            id=contract["id"],
            player_id=contract.get("player_id") or 0,
            club_id=contract.get("club_id") or 0,
            start_date=str(contract.get("contract_start") or ""),
            end_date=str(contract.get("contract_end") or ""),
            base_salary=float(contract.get("base_salary") or 0),
            bonuses=domain_bonuses,
            binding_bonus_groups=list(binding_groups.values()),
            contract_text=contract.get("contract_text") or "",
        )
        earned_bonus_ids = (
            {bonus.id for bonus in contract_model.earned_bonuses(stats_snapshot)}
            if stats_snapshot
            else set()
        )
        bonus_items = []

        for bonus in contract_bonuses:
            progress = (
                evaluate_bonus_progress(bonus, latest_stats)
                if include_progress and latest_stats
                else None
            )
            bonus_items.append(
                {
                    **dict(bonus),
                    "progress": progress,
                    "payout_value": (
                        progress["payout_value"]
                        if progress and bonus["id"] in earned_bonus_ids
                        else 0.0
                    ),
                }
            )

        items.append(
            {
                **dict(contract),
                "bonuses": bonus_items,
                "total_payout_value": (
                    contract_model.total_bonus_payout(stats_snapshot) if stats_snapshot else 0.0
                ),
            }
        )

    return items


def build_player_detail_response(player, stats, contracts, bonuses, conditions):
    contract_items = build_contract_list(
        contracts,
        bonuses,
        conditions,
        latest_stats=stats[0] if stats else None,
    )

    return {
        "player": serialize_player(player),
        "stats": stats,
        "contracts": contract_items,
        "totals": {
            "total_payout_value": sum(item["total_payout_value"] for item in contract_items),
        },
    }
