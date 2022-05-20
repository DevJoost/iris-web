#!/usr/bin/env python3
#
#  IRIS Source Code
#  Copyright (C) 2021 - Airbus CyberSecurity (SAS)
#  ir@cyberactionlab.net
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3 of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

from sqlalchemy import and_
from sqlalchemy import or_
from pprint import pprint

from app import db
from app.models import AssetsType
from app.models import CaseAssets
from app.models import CaseEventCategory
from app.models import CaseEventsAssets
from app.models import CaseEventsIoc
from app.models import CasesEvent
from app.models import EventCategory
from app.models import Ioc
from app.models import IocLink
from app.models import IocType
from app.models import User


def get_case_filter_assets(caseid):
    assets_cache = CaseAssets.query.with_entities(
        CaseEventsAssets.event_id,
        CaseAssets.asset_id,
        CaseAssets.asset_name,
        AssetsType.asset_name.label('type'),
        CaseAssets.asset_ip,
        CaseAssets.asset_description,
        CaseAssets.asset_compromised
    ).filter(
        CaseEventsAssets.case_id == caseid,
    ).join(CaseEventsAssets.asset, CaseAssets.asset_type).all()

    iocs_cache = CaseEventsIoc.query.with_entities(
        CaseEventsIoc.event_id,
        CaseEventsIoc.ioc_id,
        Ioc.ioc_value,
        Ioc.ioc_description
    ).filter(
        CaseEventsIoc.case_id == caseid
    ).join(
        CaseEventsIoc.ioc
    ).all()

    asset_cache = {}
    for asset in assets_cache:
        if asset.asset_id not in asset_cache:
            asset_cache[asset.asset_id] = [asset.asset_name, asset.type]
    ioc_cache = {}
    for ioc in iocs_cache:
        if ioc.ioc_id not in ioc_cache:
            ioc_cache[ioc.ioc_id] = [ioc.ioc_value, ioc.ioc_id]
    return asset_cache, ioc_cache

def get_case_events_query_graph(caseid, condition):
    events = CasesEvent.query.with_entities(
        CasesEvent.event_id,
        CasesEvent.event_date,
        CasesEvent.event_date_wtz,
        CasesEvent.event_tz,
        CasesEvent.event_title,
        CasesEvent.event_color,
        CasesEvent.event_tags,
        CasesEvent.event_content,
        CasesEvent.event_in_summary,
        CasesEvent.event_in_graph,
        User.user,
        CasesEvent.event_added,
        EventCategory.name.label("category_name")
    ).filter(condition).order_by(
        CasesEvent.event_date
    ).outerjoin(
        CasesEvent.category
    ).join(
        CasesEvent.user
    ).all()
    graph = []
    for event in events:
        asset_links = get_case_events_assets_graph(caseid, event_id=event.event_id)
        graph.extend(asset_links)
        ioc_links = get_case_events_ioc_graph(caseid, event_id=event.event_id)
        graph.extend(ioc_links)
    return graph

def get_case_events_assets_graph(caseid, event_id=None):
    events = CaseEventsAssets.query.with_entities(
        CaseEventsAssets.event_id,
        CasesEvent.event_title,
        CaseAssets.asset_name,
        CaseAssets.asset_id,
        AssetsType.asset_name.label('type_name'),
        AssetsType.asset_icon_not_compromised,
        AssetsType.asset_icon_compromised,
        CasesEvent.event_color,
        CaseAssets.asset_compromised,
        CaseAssets.asset_description,
        CaseAssets.asset_ip,
        CasesEvent.event_date,
        CasesEvent.event_tags
    )
    if event_id:
        events = events.filter(and_(
            CaseEventsAssets.case_id == caseid,
            CasesEvent.event_in_graph == True,
            CaseEventsAssets.event_id == event_id
        )).join(
            CaseEventsAssets.event,
            CaseEventsAssets.asset,
            CaseAssets.asset_type
        ).all()
    else:
        events = events.filter(and_(
            CaseEventsAssets.case_id == caseid,
            CasesEvent.event_in_graph == True
        )).join(
            CaseEventsAssets.event,
            CaseEventsAssets.asset,
            CaseAssets.asset_type
        ).all()
    return events


def get_case_events_ioc_graph(caseid, event_id=None):
    events = CaseEventsIoc.query.with_entities(
        CaseEventsIoc.event_id,
        CasesEvent.event_title,
        CasesEvent.event_date,
        Ioc.ioc_id,
        Ioc.ioc_value,
        Ioc.ioc_description,
        IocType.type_name
    )
    if event_id:
        events = events.filter(and_(
            CaseEventsIoc.case_id == caseid,
            CasesEvent.event_in_graph == True,
            CaseEventsIoc.event_id == event_id
        )).join(
            CaseEventsIoc.event,
            CaseEventsIoc.ioc,
            Ioc.ioc_type,
        ).all()
    else:
        events = events.filter(and_(
            CaseEventsIoc.case_id == caseid,
            CasesEvent.event_in_graph == True
        )).join(
            CaseEventsIoc.event,
            CaseEventsIoc.ioc,
            Ioc.ioc_type,
        ).all()

    return events

def get_events_by_assetname(caseid, name):
    return CaseAssets.query.with_entities(
        CaseAssets.asset_name,
        CaseAssets.asset_id,
        CaseEventsAssets.event_id
    ).filter(and_(
        CaseAssets.asset_name == name,
        CaseAssets.case_id == caseid
    )).join(
        CaseEventsAssets.asset
    ).all()

def get_events_by_assetid(caseid, asset_id):
    return CaseEventsAssets.query.with_entities(
        CaseEventsAssets.asset_id,
        CaseEventsAssets.event_id
    ).filter(and_(
        CaseEventsAssets.asset_id == asset_id,
        CaseEventsAssets.case_id == caseid
    )).all()

def get_events_by_iocid(caseid, ioc_id):
    return CaseEventsIoc.query.with_entities(
        CaseEventsIoc.ioc_id,
        CaseEventsIoc.event_id
    ).filter(and_(
        CaseEventsIoc.ioc_id == ioc_id,
        CaseEventsIoc.case_id == caseid
    )).all()

def get_events_categories():
    return EventCategory.query.with_entities(
        EventCategory.id,
        EventCategory.name
    ).all()


def get_default_cat():
    cat = EventCategory.query.with_entities(
        EventCategory.id,
        EventCategory.name
    ).filter(
        EventCategory.name == "Unspecified"
    ).first()

    return [cat._asdict()]


def get_case_event(event_id, caseid):
    return CasesEvent.query.filter(
        CasesEvent.event_id == event_id,
        CasesEvent.case_id == caseid
    ).first()


def delete_event_category(event_id):
    CaseEventCategory.query.filter(
        CaseEventCategory.event_id == event_id
    ).delete()


def get_event_category(event_id):
    cec = CaseEventCategory.query.filter(
        CaseEventCategory.event_id == event_id
    ).first()
    return cec


def save_event_category(event_id, category_id):
    CaseEventCategory.query.filter(
        CaseEventCategory.event_id == event_id
    ).delete()

    cec = CaseEventCategory()
    cec.event_id = event_id
    cec.category_id = category_id

    db.session.add(cec)
    db.session.commit()


def get_event_assets_ids(event_id, caseid):
    assets_list = CaseEventsAssets.query.with_entities(
        CaseEventsAssets.asset_id
    ).filter(
        CaseEventsAssets.event_id == event_id,
        CaseEventsAssets.case_id == caseid
    ).all()

    return [x[0] for x in assets_list]


def get_event_iocs_ids(event_id, caseid):
    iocs_list = CaseEventsIoc.query.with_entities(
        CaseEventsIoc.ioc_id
    ).filter(
        CaseEventsIoc.event_id == event_id,
        CaseEventsIoc.case_id == caseid
    ).all()

    return [x[0] for x in iocs_list]


def update_event_assets(event_id, caseid, assets_list):

    CaseEventsAssets.query.filter(
        CaseEventsAssets.event_id == event_id,
        CaseEventsAssets.case_id == caseid
    ).delete()

    for asset in assets_list:
        try:

            cea = CaseEventsAssets()
            cea.asset_id = int(asset)
            cea.event_id = event_id
            cea.case_id = caseid

            db.session.add(cea)

        except Exception as e:
            return False, str(e)

    db.session.commit()
    return True, ''


def update_event_iocs(event_id, caseid, iocs_list):

    CaseEventsIoc.query.filter(
        CaseEventsIoc.event_id == event_id,
        CaseEventsIoc.case_id == caseid
    ).delete()

    for ioc in iocs_list:
        try:

            cea = CaseEventsIoc()
            cea.ioc_id = int(ioc)
            cea.event_id = event_id
            cea.case_id = caseid

            db.session.add(cea)

        except Exception as e:
            return False, str(e)

    db.session.commit()
    return True, ''


def get_case_assets_for_tm(caseid):
    """
    Return a list of all assets linked to the current case
    :return: Tuple of assets
    """
    assets = [{'asset_name': '', 'asset_id': '0'}]

    assets_list = CaseAssets.query.with_entities(
        CaseAssets.asset_name,
        CaseAssets.asset_id,
        AssetsType.asset_name.label('type')
    ).filter(
        CaseAssets.case_id == caseid
    ).join(CaseAssets.asset_type).order_by(CaseAssets.asset_name).all()

    for asset in assets_list:
        assets.append({
            'asset_name': "{} ({})".format(asset.asset_name, asset.type),
            'asset_id': asset.asset_id
        })

    return assets


def get_case_iocs_for_tm(caseid):
    iocs = [{'ioc_value': '', 'ioc_id': '0'}]

    iocs_list = Ioc.query.with_entities(
        Ioc.ioc_value,
        Ioc.ioc_id
    ).filter(
        IocLink.case_id == caseid
    ).join(
        IocLink.ioc
    ).order_by(
        Ioc.ioc_value
    ).all()

    for ioc in iocs_list:
        iocs.append({
            'ioc_value': "{}".format(ioc.ioc_value),
            'ioc_id': ioc.ioc_id
        })

    return iocs