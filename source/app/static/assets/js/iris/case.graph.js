var graph_filter = ace.edit("graph_filtering",
{
    autoScrollEditorIntoView: true,
    minLines: 1,
    maxLines: 5
});
graph_filter.setTheme("ace/theme/tomorrow");
graph_filter.session.setMode("ace/mode/json");
graph_filter.renderer.setShowGutter(false);
graph_filter.setShowPrintMargin(false);
graph_filter.renderer.setScrollMargin(10, 10);
graph_filter.setOption("displayIndentGuides", true);
graph_filter.setOption("indentedSoftWrap", true);
graph_filter.setOption("showLineNumbers", false);
graph_filter.setOption("placeholder", "Filter timeline");
graph_filter.setOption("highlightActiveLine", false);
graph_filter.commands.addCommand({
                    name: "Do filter",
                    bindKey: { win: "Enter", mac: "Enter" },
                    exec: function (editor) {
                              filter_timeline();
                    }
});

function get_full_case_graph() {
    get_request_api('graph/getdata')
    .done((data) => {
            if (data.status == 'success') {
                redrawGraph(data.data);
                fillfilter(data.data);
                hide_loader();
            } else {
                $('#submit_new_asset').text('Save again');
                swal("Oh no !", data.message, "error")
            }
        })
}

function get_nodes_by_asset(asset_id) {
    get_request_api('graph/getdata/byasset/'+asset_id).done()
    .done((data) => {
            if (data.status == 'success') {
                addToGraph(data.data.nodes,data.data.edges);
                hide_loader();
            } else {
                $('#submit_new_asset').text('Save again');
                swal("Oh no !", data.message, "error")
            }
        })
}

var network;

var nodes;
var edges;

function sortAlphabet(str) {
  var return_val = [...str].sort().join("");
  return return_val
}

function addToGraph(add_nodes,add_edges) {
    for (let i = 0; i < add_nodes.length; i++){
        if(!nodes.some(_node => _node.id === add_nodes[i].id)){
            nodes.push(add_nodes[i]);
        }
    }
    for (let i = 0; i < add_edges.length; i++){
        sorted_add_to_from = sortAlphabet(add_edges[i].from+add_edges[i].to)
        if(!edges.some(_edge => sortAlphabet(_edge.from+_edge.to) === sorted_add_to_from)){
            edges.push(add_edges[i]);
        }
    }
    data = {
      "nodes": nodes,
      "edges": edges
    };
    redrawGraph(data);
}


function fillfilter(data) {
  var standard_filters = [
              {value: 'asset:', score: 10, meta: 'Match assets of events'},
              {value: 'startDate:', score: 10, meta: 'Match end date of events'},
              {value: 'endDate:', score: 10, meta: 'Match end date of events'},
              {value: 'tag:', score: 10, meta: 'Match tag of events'},
              {value: 'description:', score: 10, meta: 'Match description of events'},
              {value: 'category:', score: 10, meta: 'Match category of events'},
              {value: 'title:', score: 10, meta: 'Match title of events'},
              {value: 'source:', score: 10, meta: 'Match source of events'},
              {value: 'raw:', score: 10, meta: 'Match raw data of events'},
              {value: 'ioc:', score: 10, meta: "Match ioc in events"},
              {value: 'AND ', score: 10, meta: 'AND operator'}
            ]
  for (rid in data.assets) {
      standard_filters.push(
           {value: data.assets[rid][0], score: 1, meta: data.assets[rid][1]}
      );
  }
  for (rid in data.categories) {
      standard_filters.push(
           {value: data.categories[rid], score: 1, meta: "Event category"}
      );
  }
  graph_filter.setOptions({
        enableBasicAutocompletion: [{
          getCompletions: (editor, session, pos, prefix, callback) => {
            callback(null, standard_filters);
          },
        }],
        enableLiveAutocompletion: true,
  });
}

function redrawGraph(data) {
  if (data.nodes.length == 0) {
        $('#card_main_load').show();
        $('#graph-container').text('No events in graph');
        hide_loader();
        return true;
  }
  var container = document.getElementById("graph-container");
  var options = {
    edges: {
      smooth: {
            enabled: true,
            type: 'continuous',
            roundness: 0.5
        }
    },
    layout: {
        randomSeed: 2,
        improvedLayout: true
    },
    interaction: {
      hideEdgesOnDrag: false
    },
    width: (window.innerWidth - 400) + "px",
    height: (window.innerHeight- 250) + "px",
    "physics": {
    "forceAtlas2Based": {
      "gravitationalConstant": -167,
      "centralGravity": 0.04,
      "springLength": 0,
      "springConstant": 0.02,
      "damping": 0.9
    },
    "minVelocity": 0.41,
    "solver": "forceAtlas2Based",
    "timestep": 0.45
    }
  };

  nodes = data.nodes;
  edges = data.edges;
  network_data = {
    "nodes": nodes,
    "edges": edges
  };
  network = new vis.Network(container, network_data, options);

  network.on("stabilizationIterationsDone", function () {
        network.setOptions( { physics: false } );
    });
  network.on("doubleClick", function (params) {
    console.log(
      "doubleClick event," + JSON.stringify(
        params,
        null,
        4
      )
    );
    if (params.nodes.length == 1) {
      get_nodes_by_asset(params.nodes[0].substring(1));
    }
  });
}

function split_bool(split_str) {
    and_split = split_str.split(' AND ');

    if (and_split[0]) {
      return and_split[0];
    }

    or_split = split_str.split(' OR ');

    if (or_split[0]) {
      return or_split[0].trim();
    }

    return null;
}

var parsed_filter = {};
var keywords = ['asset', 'tag', 'title', 'description', 'ioc', 'raw', 'category', 'source', 'startDate', 'endDate'];

function parse_filter(str_filter, keywords) {
  for (var k = 0; k < keywords.length; k++) {
  	keyword = keywords[k];
    items = str_filter.split(keyword + ':');

    ita = items[1];

    if (ita === undefined) {
    	continue;
    }

    item = split_bool(ita);

    if (item != null) {
      if (!(keyword in parsed_filter)) {
        parsed_filter[keyword] = [];
      }
      if (!parsed_filter[keyword].includes(item)) {
        parsed_filter[keyword].push(item.trim());
        console.log('Got '+ item.trim() + ' as ' + keyword);
      }

      if (items[1] != undefined) {
        str_filter = str_filter.replace(keyword + ':' + item, '');
        if (parse_filter(str_filter, keywords)) {
        	keywords.shift();
        }
      }
    }
  }
  return true;
}

function filter_graph() {
    current_path = location.protocol + '//' + location.host + location.pathname;
    new_path = current_path + case_param() + '&filter=' + encodeURIComponent(graph_filter.getValue());
    window.location = new_path;
}

function reset_filters() {
    current_path = location.protocol + '//' + location.host + location.pathname;
    new_path = current_path + case_param();
    window.location = new_path;
}


function apply_filtering() {
    keywords = ['asset', 'tag', 'title', 'description', 'ioc', 'category', 'source',  'raw', 'startDate', 'endDate'];
    parsed_filter = {};
    parse_filter(graph_filter.getValue(), keywords);
    filter_query = encodeURIComponent(JSON.stringify(parsed_filter));
    show_loader();
    get_request_data_api("/case/graph/advanced-filter",{ 'q': filter_query })
    .done((data) => {
        if (data.status == 'success') {
            fillfilter(data.data);
            redrawGraph(data.data);
            hide_loader();
        } else {
            $('#submit_new_asset').text('Save again');
            swal("Oh no !", data.message, "error")
        }
    });

}

function getFilterFromLink(){
    queryString = window.location.search;
    urlParams = new URLSearchParams(queryString);
    if (urlParams.get('filter') !== undefined) {
        return urlParams.get('filter')
    }
    return null;
}

function get_or_filter_graph() {
    filter = getFilterFromLink();
    if (filter) {
        graph_filter.setValue(filter);
        apply_filtering();
    } else {
        get_full_case_graph();
    }
}




/* Page is ready, fetch the assets of the case */
$(document).ready(function(){
    get_or_filter_graph();
});

