# Home Network Inventory
# Topology node positions CRUD.
#
# Copyright (C) Mike Petrichenko
# e-mail: btframework@gmail.com
# Project repository: https://github.com/DroneTales/HomeNetworkInventory
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy.orm import Session

from app.models.device import Device
from app.models.topology_position import TopologyPosition


def list_by_site(db: Session, site_id: int) -> list[TopologyPosition]:
    return (
        db.query(TopologyPosition)
        .filter(TopologyPosition.site_id == site_id)
        .all()
    )


def upsert_many(
    db: Session,
    site_id: int,
    positions: list[dict],
) -> int:
    device_ids = [int(p["device_id"]) for p in positions]
    known = {
        d.id
        for d in db.query(Device.id).filter(
            Device.site_id == site_id, Device.id.in_(device_ids)
        ).all()
    }

    existing = {
        row.device_id: row
        for row in db.query(TopologyPosition)
        .filter(
            TopologyPosition.site_id == site_id,
            TopologyPosition.device_id.in_(device_ids),
        )
        .all()
    }

    updated = 0
    for p in positions:
        device_id = int(p["device_id"])
        if device_id not in known:
            continue
        x = float(p["x"])
        y = float(p["y"])
        row = existing.get(device_id)
        if row is None:
            row = TopologyPosition(
                site_id=site_id, device_id=device_id, x=x, y=y
            )
            db.add(row)
        else:
            row.x = x
            row.y = y
        updated += 1

    db.flush()
    return updated


def clear_site(db: Session, site_id: int) -> int:
    deleted = (
        db.query(TopologyPosition)
        .filter(TopologyPosition.site_id == site_id)
        .delete(synchronize_session=False)
    )
    db.flush()
    return deleted
