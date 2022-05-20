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

import itertools
import json
from datetime import datetime
import urllib.parse
from flask import Blueprint, request
from flask import redirect
from flask import render_template
from flask import url_for
from flask_wtf import FlaskForm
from sqlalchemy import and_
from pprint import pprint

from app.datamgmt.case.case_db import get_case
from app.datamgmt.case.case_events_db import get_case_events_assets_graph
from app.datamgmt.case.case_events_db import get_case_events_ioc_graph
from app.datamgmt.case.case_events_db import get_case_events_query_graph
from app.datamgmt.case.case_events_db import get_case_filter_assets
from app.datamgmt.case.case_events_db import get_events_by_assetname
from app.datamgmt.case.case_events_db import get_events_categories
from app.datamgmt.case.case_events_db import get_events_by_assetid
from app.datamgmt.case.case_events_db import get_events_by_iocid
from app.iris_engine.utils.common import parse_bf_date_format
from app.util import api_login_required
from app.util import login_required
from app.util import response_success
from app.util import response_error
from app.models import CasesEvent
from app.models import EventCategory

case_graph_blueprint = Blueprint('case_graph',
                                 __name__,
                                 template_folder='templates')


# CONTENT ------------------------------------------------
@case_graph_blueprint.route('/case/graph', methods=['GET'])
@login_required
def case_graph(caseid, url_redir):
    if url_redir:
        return redirect(url_for('case_graph.case_graph', cid=caseid, redirect=True))

    case = get_case(caseid)
    form = FlaskForm()

    return render_template("case_graph.html", case=case, form=form)

def make_graph_info(caseid, events):
    nodes = []
    edges = []
    dates = {
        "human": [],
        "machine": []
    }

    tmp = {}
    for event in events:
        if hasattr(event, 'asset_compromised'):
            if event.asset_compromised:
                img = event.asset_icon_compromised
                # is_master_atype = True

            elif not event.asset_compromised:
                img = event.asset_icon_not_compromised
                # is_master_atype = False

            else:
                img = 'question-mark.png'

            if event.asset_ip:
                title = "{} -{}".format(event.asset_ip, event.asset_description)
            else:
                title = "{}".format(event.asset_description)
            label = event.asset_name
            idx = f'a{event.asset_id}'
            node_type = 'asset'

        else:
            img = 'virus-covid-solid.png'
            label = event.ioc_value
            title = event.ioc_description
            idx = f'b{event.ioc_id}'
            node_type = 'ioc'

        try:
            date = "{}-{}-{}".format(event.event_date.day, event.event_date.month, event.event_date.year)
        except:
            date = '15-05-2021'

        if date not in dates:
            dates['human'].append(date)
            dates['machine'].append(datetime.timestamp(event.event_date))

        new_node = {
            'id': idx,
            'label': label,
            'image': '/static/assets/img/graph/' + img,
            'shape': 'image',
            'title': title,
            'value': 1
        }
        if not any(node['id'] == idx for node in nodes):
            nodes.append(new_node)

        ak = {
            'node_id': idx,
            'node_title': "{} - {}".format(event.event_date, event.event_title),
            'node_name': label,
            'node_type': node_type
        }
        if tmp.get(event.event_id):
            tmp[event.event_id]['list'].append(ak)

        else:
            tmp[event.event_id] = {
                'master_node': [],
                'list': [ak]
            }

    for event_id in tmp:
        for subset in itertools.combinations(tmp[event_id]['list'], 2):

            if subset[0]['node_type'] == 'ioc' and subset[1]['node_type'] == 'ioc' and len(tmp[event_id]['list']) != 2:
                continue

            edge = {
                'from': subset[0]['node_id'],
                'to': subset[1]['node_id'],
                'title': subset[0]['node_title'],
                'dashes': subset[0]['node_type'] == 'ioc' or subset[1]['node_type'] == 'ioc'
            }
            edges.append(edge)
    assets, iocs = get_case_filter_assets(caseid)
    resp = {
        'nodes': nodes,
        'edges': edges,
        'dates': dates,
        'assets': assets,
        'iocs': iocs,
        "categories": [cat.name for cat in get_events_categories()]
    }
    return resp


@case_graph_blueprint.route('/case/graph/getdata', methods=['GET'])
@api_login_required
def case_graph_get_data(caseid):
    events = get_case_events_assets_graph(caseid)
    print("EVENTS")
    pprint(events)
    events.extend(get_case_events_ioc_graph(caseid))
    print("EVENTS_EXTENDED")
    pprint(events)
    resp = make_graph_info(caseid, events)
    print("RESP")
    pprint(resp)
    return response_success("", data=resp)


@case_graph_blueprint.route('/case/graph/getdata/byasset/<int:asset_id>', methods=['GET'])
@api_login_required
def case_graph_get_data_by_asset(asset_id, caseid):
    event_ids = get_events_by_assetid(caseid, asset_id)
    events = []
    for event_id in event_ids:
        events.extend(get_case_events_assets_graph(caseid, event_id.event_id))
        events.extend(get_case_events_ioc_graph(caseid, event_id.event_id))
    events = list(set(events))
    print("EVENTS")
    pprint(events)
    resp = make_graph_info(caseid, events)
    print("RESP")
    pprint(resp)
    return response_success("", data=resp)

@case_graph_blueprint.route('/case/graph/advanced-filter', methods=['GET'])
@api_login_required
def case_filter_timeline(caseid):
    args = request.args.to_dict()
    query_filter = args.get('q')

    try:
        filter_d = dict(json.loads(urllib.parse.unquote_plus(query_filter)))
    except Exception as e:
        return response_error('Invalid query string')

    assets = filter_d.get('asset')
    iocs = filter_d.get('ioc')
    tags = filter_d.get('tag')
    descriptions = filter_d.get('description')
    categories = filter_d.get('category')
    raws = filter_d.get('raw')
    start_date = filter_d.get('startDate')
    end_date = filter_d.get('endDate')
    titles = filter_d.get('title')
    sources = filter_d.get('source')

    condition = (CasesEvent.case_id == caseid)

    if tags:
        for tag in tags:
            condition = and_(condition,
                             CasesEvent.event_tags.ilike(f'%{tag}%'))

    if titles:
        for title in titles:
            condition = and_(condition,
                             CasesEvent.event_title.ilike(f'%{title}%'))

    if sources:
        for source in sources:
            condition = and_(condition,
                             CasesEvent.event_source.ilike(f'%{source}%'))

    if descriptions:
        for description in descriptions:
            condition = and_(condition,
                             CasesEvent.event_content.ilike(f'%{description}%'))

    if raws:
        for raw in raws:
            condition = and_(condition,
                             CasesEvent.event_raw.ilike(f'%{raw}%'))

    if start_date:
        try:
            parsed_start_date = parse_bf_date_format(start_date[0])
            condition = and_(condition,
                             CasesEvent.event_date >= parsed_start_date)

        except Exception as e:
            print(e)
            pass

    if end_date:
        try:
            parsed_end_date = parse_bf_date_format(end_date[0])
            condition = and_(condition,
                             CasesEvent.event_date <= parsed_end_date)
        except Exception as e:
            pass

    if categories:
        for category in categories:
            condition = and_(condition,
                             EventCategory.name == category)

    events = get_case_events_query_graph(caseid, condition)
    print("EVENTS")
    pprint(events)
    asset_filtered = []
    if assets:
        for asset in assets:
            for event_by_asset in get_events_by_assetname(caseid, asset):
                asset_filtered.append(event_by_asset.event_id)
    ioc_filtered = []
    if iocs:
        iocs = [ioc.lower() for ioc in iocs]

    final_events = []
    print("asset_filtered")
    pprint(asset_filtered)
    for unfil_event in events:
        if len(asset_filtered) > 0:
            if unfil_event.event_id not in asset_filtered:
                continue
        final_events.append(unfil_event)
    print("FINAL_EVENTS")
    pprint(final_events)

    resp = make_graph_info(caseid, final_events)
    print("RESP")
    pprint(resp)

    return response_success("", data=resp)
