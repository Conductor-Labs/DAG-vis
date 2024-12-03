import streamlit as st
import json
from streamlit_flow import streamlit_flow
from streamlit_flow.elements import StreamlitFlowNode, StreamlitFlowEdge
from streamlit_flow.state import StreamlitFlowState
from streamlit_flow.layouts import LayeredLayout


#test 

st.set_page_config(
    page_title="Techno-Economic Analysis App",
    page_icon="💡",
    layout="wide",
)
# File uploader
uploaded_file = st.file_uploader("Choose a DAG JSON file", type=["json"])

if uploaded_file is not None:
    # Read JSON
    try:
        data = json.load(uploaded_file)
    except Exception as e:
        st.error(f"Error reading JSON file: {e}")
        st.stop()
    
    # Extract nodes and edges
    nodes_data = data.get('nodes', [])
    edges_data = data.get('edges', [])
    
    # Collect node IDs for validation
    node_ids = set()
    for node in nodes_data:
        node_id = node.get('unit_operation_id', '')
        if node_id:
            node_ids.add(node_id)
    
    # Map nodes to StreamlitFlowNodes
    nodes = []
    for node in nodes_data:
        node_id = node.get('unit_operation_id', '')
        node_name = node.get('name', '')
        if not node_id:
            continue  # Skip nodes without an ID
        
        # Determine node type
        node_type = 'default'
        if not any(edge['target'] == node_id for edge in edges_data):
            node_type = 'input'  # Nodes with no incoming edges
        if not any(edge['source'] == node_id for edge in edges_data):
            node_type = 'output'  # Nodes with no outgoing edges
        
        # Set source and target positions
        source_position = 'right'
        target_position = 'left'
        
        st_node = StreamlitFlowNode(
            id=node_id,
            pos=(0, 0),
            data={'content': node_name},
            node_type=node_type,
            source_position=source_position,
            target_position=target_position
        )
        nodes.append(st_node)
        
    # Map edges to StreamlitFlowEdges
    edges = []
    for edge in edges_data:
        edge_id = edge.get('edge_id', '')
        source = edge.get('source', '')
        target = edge.get('target', '')
        stream_type = edge.get('stream_type', '')
        animated = True if stream_type == 'core' else False
        if source not in node_ids or target not in node_ids:
            st.warning(f"Edge {edge_id} refers to unknown node(s): source={source}, target={target}")
            continue  # Skip edges with unknown nodes
        st_edge = StreamlitFlowEdge(
            id=edge_id,
            source=source,
            target=target,
            animated=animated
        )
        edges.append(st_edge)
        
    # Create state
    state = StreamlitFlowState(nodes, edges)
    
    # Visualize flow using LayeredLayout with direction 'right'
    streamlit_flow(
        'dag_layout',
        state,
        layout=LayeredLayout(direction='right'),
        fit_view=True
    )
